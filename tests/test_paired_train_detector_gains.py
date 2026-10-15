"""Pair actual executed detector observations; missing coverage is never padded."""
import json
from copy import deepcopy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def actual_variants():
    base=ROOT/'reports/cohort_rebuild_v2/experiments/20261015T161923-4650ee37'
    return {name:json.loads((base/(name+'.json')).read_text(encoding='utf-8'))['observations'] for name in ('structural','repeated','full')}

def test_actual_gain_comparison_uses_exact_shared_identities():
    from scripts.measure_paired_train_detector_gains import paired_metrics
    variants=actual_variants();result=paired_metrics(variants)
    expected=set.intersection(*(set(r['identity'] for r in rows) for rows in variants.values()))
    assert result['n']==len(expected)
    assert set(result['paired_identities'])==expected
    assert all(v['n']==len(expected) for v in result['metrics'].values())
    assert result['scope']=='Observed complete-case TRAIN comparison only'

def test_duplicate_or_conflicting_actual_observations_are_rejected():
    from scripts.measure_paired_train_detector_gains import paired_metrics
    variants=actual_variants();variants['full'].append(deepcopy(variants['full'][0]))
    with pytest.raises(ValueError,match='Duplicate'):paired_metrics(variants)
    variants=actual_variants();variants['full'][0]['label']=not variants['full'][0]['label']
    with pytest.raises(ValueError,match='labels'):paired_metrics(variants)
