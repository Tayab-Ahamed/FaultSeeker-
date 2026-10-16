.PHONY: test evidence-demo judge

test:
	python -m pytest tests -q -p no:cacheprovider

evidence-demo:
	python scripts/run_evidence_upgrade.py

judge:
	python scripts/reproduce/run_all.py
