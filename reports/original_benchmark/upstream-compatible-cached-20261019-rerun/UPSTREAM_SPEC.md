# Pinned upstream ranking specification

Source commit: `72753bd833554449efa8499f0d1775a97fb5c696`

Primary source:

- `https://raw.githubusercontent.com/kairanskrr/FaultSeeker/72753bd833554449efa8499f0d1775a97fb5c696/faultseeker/function_analysis/function_ranker.py`

Related upstream sources inspected:

- `faultseeker/function_analysis/function_analyzer.py`
- `faultseeker/prompts/function_analysis/vulnerability_analysis_prompts.py`
- `faultseeker/forensics/orchestrator.py`
- `faultseeker/forensics/trace_analyzer.py`
- `faultseeker/data_collection/txn_replayer.py`
- `faultseeker/data_collection/txn_sequencer.py`
- `faultseeker/data_collection/trace_parser.py`
- `faultseeker/data_collection/contract_downloader.py`
- `faultseeker/utils/agent.py`

## Deterministic ranker

For ordinary candidates, upstream constructs the key:

```text
function + "_" + address
```

and counts distinct stringified call-depth paths for that key. Candidates are
sorted by `count` descending. Python's stable sort preserves encounter order
for equal counts. Gas, parameters, depth magnitude, source evidence, and LLM
confidence do not contribute to the deterministic count ordering.

If no ordinary candidate survives, upstream falls back to every key in
`function_call_loc_memo`, transforms `::` to `_`, and counts every memo entry
without depth deduplication.

Created-contract candidates are kept in a separate map keyed by function name.
The `RankingResult` fields are:

```text
repeated_patterns
address_calls_with_created_contract_in_params
functions_to_be_inspected
address_list
```

The upstream result has no numeric `rank` field. Rank is the insertion order of
the sorted `functions_to_be_inspected` mapping.

## Paper metric reconstruction

The pinned upstream repository did not publish an evaluation script. This run
therefore uses the narrowest evidence-bounded reconstruction supported by the
paper and labels:

- compare raw candidate function identifiers against any labeled function name;
- do not require candidate address equality;
- do not resolve four-byte selectors to names;
- count a hit when any target appears in the first k candidates;
- keep all 115 files in the denominator, including failures as zero.

The saved provider-pinned predictions are reused as inputs. They are not
re-ranked from raw upstream traces because those traces and the authors' full
standalone evaluator were not released. The current address-aware diagnostic
metric is reported alongside the reconstruction and is not replaced.
