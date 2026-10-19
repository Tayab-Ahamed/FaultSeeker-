# Cached original-benchmark upstream-compatible evaluation

Source commit: `72753bd833554449efa8499f0d1775a97fb5c696`

This report reuses saved provider-pinned predictions and never calls RPC, cast, or models.
The upstream evaluator was not published; the primary reconstruction compares raw function identifiers by name only.

| Metric | Hits | N | Percentage |
|---|---:|---:|---:|
| Upstream reconstruction R@1 | 27 | 115 | 23.48% |
| Upstream reconstruction R@3 | 49 | 115 | 42.61% |
| Upstream reconstruction R@5 | 53 | 115 | 46.09% |
| Current address-aware R@1 | 25 | 115 | 21.74% |
| Current address-aware R@3 | 49 | 115 | 42.61% |
| Current address-aware R@5 | 52 | 115 | 45.22% |

## Paper comparison

| Metric | Reconstructed hits | Paper target hits | Difference |
|---|---:|---:|---:|
| recall_at_1 | 27 | 58 | -31 |
| recall_at_3 | 49 | 85 | -36 |
| recall_at_5 | 53 | 88 | -35 |

## Failure-stage counts

```json
{
  "data_collection_or_trace_replay": 5,
  "final_ranking_or_ground_truth_mismatch": 43,
  "none": 67
}
```
