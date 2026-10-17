# Original FaultSeeker benchmark attribution

This directory contains an unmodified copy of the 115 function-localization
ground-truth JSON files and `benchmark_classification.csv` from the original
FaultSeeker repository:

- Repository: <https://github.com/kairanskrr/FaultSeeker>
- Retrieved commit: `72753bd833554449efa8499f0d1775a97fb5c696`
- Paper context: FaultSeeker, ASE 2025
- License: see [`third_party/original_faultseeker/LICENSE`](../../third_party/original_faultseeker/LICENSE)
- Upstream README: [`third_party/original_faultseeker/README.md`](../../third_party/original_faultseeker/README.md)

The files are retained for a **new measurement on the original benchmark**.
They are not being presented as proof of the implementation paper's separate
246-row cohort or its reported detector/cost values.

## Modifications

The imported JSON and CSV files were copied byte-for-byte from the retrieved
upstream commit. No labels, locations, transaction ordering, or source fields
were changed. The surrounding evaluation harness and reports in this
repository are new work by this project and are not part of the upstream
release.
