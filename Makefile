.PHONY: test validate-cohort evidence-demo judge upstream-validate selective-localization

test:
	python -m pytest tests -q -p no:cacheprovider

validate-cohort:
	python -m benchmark.validate_cohort_manifest benchmark/cohort_manifest.json --root .

evidence-demo:
	python scripts/run_evidence_upgrade.py

judge:
	python scripts/reproduce/run_all.py

upstream-validate:
	python scripts/reproduce/independent_upstream_validation.py

selective-localization:
	python scripts/research/evaluate_selective_localization.py
