# Scoped original runtime cache audit

Inspected only main checkout reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/.workers. The top-level .workers path does not exist; the pinned run contains the ignored worker cache.

77 worker run directories contain241 files:77 manifests,77 state files,77 raw JSON rows,10 mismatch JSONL files. There are no separate text/log/runtime trace files in this tree.74 raw filenames match the original110-success transaction allowlist.64 of those contain cast metadata;10 contain no cast payload. The64 cast blocks expose output_tail and stderr_tail plus provider/exit metadata.61 output tails are exactly1200 characters; the other nonempty lengths are895,768,1008. No output tail exceeds1200.

Auditing allowlisted rows in worker manifests as well as raw rows yields149 records with max output tail1200 and max stderr tail628. No row has a path/log/trace/file reference other than its excluded annotation filename. Worker state files contain counters, run_id and state only, with no runtime-file references. JSONL mismatch records were not used as feature inputs. The audit records file hashes and relative paths in cache_audit.json.

No complete raw trace was found within the authorized scope. This establishes an evidence limitation for this cache only, not proof that full traces do not exist elsewhere. No labels were used to choose runtime candidates and no new feature experiment was run because richer input was not found. No RPC, network, other benchmark batches, source fetching or global search occurred.
