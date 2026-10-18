# Generic decoder admission decision

Existing data/models/selector_cache.json has947 selector-to-name entries and no
provenance, request records, or raw response bindings. Git history for this cache
and fetch script begins at snapshot6282729. The script reads saved prediction
selectors, calls the generic 4byte.directory API, and merges pre-existing cache
entries without proving their origins. Its generic logic alone cannot establish
the acquisition independence of every persisted entry. Existing cache is not
admitted as a trustworthy prospective lexical decoder. No live requests made.

Future acquisition specification, to be frozen before any future-cohort score:

- Inputs: unique literal four-byte runtime selectors only, gathered independently
  of targets, annotations, incident names, and decoded GT function names.
- Generic endpoint already used by repository code:
  https://www.4byte.directory/api/v1/signatures/?hex_signature=SELECTOR
- Persist request URL, selector, UTC request time, HTTP status, complete raw body,
  SHA256 body digest, and acquisition-script digest. Follow pagination completely
  before applying a collision policy; bind each page and do not infer absence
  from a failed or partial request.
- Conservative fixed collision policy: admit a display name only for one unique
  valid canonical text signature across all returned records; ambiguous or
  missing responses yield empty decoded_name. Keep the alternatives in provenance.
  This prospective policy differs from the old earliest-ID script and therefore
  requires retraining/revalidation, not reuse of reported lexical performance.
- Output keeps selector literal unchanged for function evaluation and adds a
  separate decoded_name for lexical features. No replacement of function identity
  with a registry guess; a generic signature does not prove contract ABI identity.
- Freeze full acquisition artifact and policy hashes before model fitting and
  future-cohort evaluation. Apply exactly the same decoder to aligned original
  runtime selectors and future runtime selectors. Saved decoded original names
  without their literal selectors are insufficient for parity.

No cohort E or other new batch was acquired or inspected. This document specifies
the unresolved transport/provenance requirement; it does not claim the registry
was contacted, cache was verified, or lexical performance transfers to fresh RPC.
