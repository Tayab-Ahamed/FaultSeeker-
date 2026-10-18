# Response-bound generic decoder preregistration

No network or empirical evaluation in this step. Supersedes the prospective
unique-signature policy in DECODER_REQUIREMENTS.md by explicit instruction:
verify candidate text signatures with installed Ethereum Keccak against the
literal runtime selector, then choose smallest numeric registry ID; lexical
signature breaks ID ties. Preserve literal selector separately, expose decoded
name only as generic semantics, retain collision count and chosen signature.

Require SHA256-bound complete saved response pages, exact selector query URL,
UTC acquisition time and successful status; incomplete pagination is rejected.
Unknown, malformed or unverified signatures produce empty decoded_name. Never
load old947-entry cache. No target/name/incident input to acquisition or decoder.
Future collection must request ALL observed selectors without target filtering,
retain full response bodies and metadata, throttle, back off on transient limits,
and stop on billing/quota exhaustion. Freeze before any new-cohort scoring.
Generic registry names are not verified ABI; collision disambiguation is a
deterministic guess, not proof of the executing function. Fixtures give no scores.
