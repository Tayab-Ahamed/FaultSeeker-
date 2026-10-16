"""Durable pre-call reservations for the cumulative paid experiment cap."""

from __future__ import annotations

import json
import math
import os
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


class BudgetApprovalRequired(RuntimeError):
    """A cloud call requires explicit approval to raise the cumulative cap."""


class DispatchNotStarted(RuntimeError):
    """Trusted pre-dispatch guard refusal; no remote request was attempted."""


class SpendGuard:
    def __init__(self, ledger_path=None, limit_usd=10.0, pricing=None):
        default_ledger = Path(__file__).resolve().parents[2] / 'data/research/spend_ledger.json'
        self.ledger_path = Path(ledger_path or os.environ.get(
            "FAULTSEEKER_SPEND_LEDGER", str(default_ledger)))
        self.limit_usd = self._amount(limit_usd)
        self.pricing = pricing or {}

    @staticmethod
    def _amount(value):
        try:
            amount = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Spend values must be finite and nonnegative") from exc
        if not math.isfinite(amount) or amount < 0:
            raise ValueError("Spend values must be finite and nonnegative")
        return amount

    @staticmethod
    def _tokens(value):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("Token counts must be nonnegative integers")
        return value

    def _price(self, model, prompt_tokens, completion_tokens):
        if model not in self.pricing:
            raise ValueError(f"Unknown cloud pricing for {model}")
        rates = self.pricing[model]
        return (self._tokens(prompt_tokens) * self._amount(rates['input']) +
                self._tokens(completion_tokens) * self._amount(rates['output'])) / 1_000_000

    @contextmanager
    def _locked(self):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.ledger_path.with_suffix(self.ledger_path.suffix + '.lock')
        with open(lock_path, 'a+b') as handle:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                self._acquire_windows_lock(handle, msvcrt)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                # Reading a byte locked by another Windows process raises
                # PermissionError. Initialize only after acquiring the lock.
                if handle.read(1) == b'':
                    handle.write(b'0')
                    handle.flush()
                yield
            finally:
                handle.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _acquire_windows_lock(handle, api, timeout_seconds=60):
        # The CRT blocking lock has a fixed retry window and can starve the
        # Python thread holding the lock. Nonblocking retries explicitly yield
        # between attempts; no ledger read or dispatch occurs before acquisition.
        deadline = time.monotonic() + timeout_seconds
        while True:
            handle.seek(0)
            try:
                api.locking(handle.fileno(), api.LK_NBLCK, 1)
                return
            except OSError as error:
                if error.errno not in (11, 13, 36):
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError('Spend ledger lock unavailable; dispatch refused') from None
                time.sleep(0.02)

    def _read(self):
        if not self.ledger_path.exists():
            return {'spent_usd': 0.0, 'reservations': {}, 'events': []}
        with open(self.ledger_path, encoding='utf-8') as handle:
            state = json.load(handle)
        if not isinstance(state, dict) or not isinstance(state.get('reservations'), dict):
            raise ValueError('Invalid spend ledger; refusing to reset it')
        self._amount(state['spent_usd'])
        for item in state['reservations'].values():
            self._amount(item['reserved_usd'])
        return state

    def _write(self, state):
        fd, temp_name = tempfile.mkstemp(prefix='.spend-', dir=self.ledger_path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump(state, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.replace(temp_name, self.ledger_path)
            except PermissionError:
                # Some managed Windows volumes forbid replace even while our
                # separate ledger lock is held. A partial direct write fails
                # closed on the next read instead of resetting spent amount.
                with open(self.ledger_path, 'w', encoding='utf-8') as handle:
                    json.dump(state, handle, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def reserve(self, model, prompt_tokens, max_completion_tokens):
        estimate = self._price(model, prompt_tokens, max_completion_tokens)
        if estimate <= 0:
            raise ValueError('Cloud reservation requires a positive known price')
        with self._locked():
            state = self._read()
            pending = sum(self._amount(r['reserved_usd']) for r in state['reservations'].values())
            if state['spent_usd'] + pending + estimate > self.limit_usd:
                raise BudgetApprovalRequired(
                    f'Cloud call would exceed ${self.limit_usd:.2f} cumulative paid cap')
            reservation = uuid.uuid4().hex
            state['reservations'][reservation] = {
                'model': model, 'reserved_usd': estimate, 'created_at': time.time()}
            state['events'].append({'event': 'reserve', 'id': reservation, 'model': model,
                                    'amount_usd': estimate})
            self._write(state)
            return reservation

    def cancel_undispatched(self, reservation):
        """Release only a reservation whose provider refused before dispatch."""
        with self._locked():
            state=self._read();item=state['reservations'].pop(reservation)
            state['events'].append({'event':'cancel-undispatched','id':reservation,
                'model':item['model'],'amount_usd':0.0,'usage_source':'not-dispatched'})
            self._write(state)
        return 0.0

    def settle(self, reservation, prompt_tokens=None, completion_tokens=None, failed=False):
        with self._locked():
            state = self._read()
            item = state['reservations'].pop(reservation)
            measured = prompt_tokens is not None and completion_tokens is not None
            amount = (self._price(item['model'], prompt_tokens, completion_tokens)
                      if measured else self._amount(item['reserved_usd']))
            state['spent_usd'] += amount
            state['events'].append({'event': 'settle', 'id': reservation,
                                    'model': item['model'], 'amount_usd': amount,
                                    'failed': bool(failed),
                                    'usage_source': 'provider' if measured else 'reservation'})
            self._write(state)
            if state['spent_usd'] > self.limit_usd:
                raise BudgetApprovalRequired('Measured usage exceeded the reserved budget')
            return amount

    def report(self):
        with self._locked():
            state = self._read()
            return {'spent_usd': state['spent_usd'],
                    'reserved_usd': sum(r['reserved_usd'] for r in state['reservations'].values()),
                    'limit_usd': self.limit_usd, 'events': list(state['events'])}
