import unittest
from unittest.mock import patch
from scripts.research import evaluate_names_nested as nested


class NestedTests(unittest.TestCase):
    def test_outer_data_never_reaches_fit_or_selection(self):
        rows = [{'targets':['a'], 'index':i} for i in range(5)]
        rows[0] = {'index':0}  # Reading outer targets would fail.
        folds = dict(enumerate(range(5)))
        seen = []
        def fit(records, indices, c, scale):
            self.assertNotIn(0, indices)
            self.assertEqual(len(indices), 3)
            seen.append(indices)
            return None
        def predict(model, row, scale):
            self.assertNotEqual(row['index'], 0)
            return ['a']
        with patch.object(nested.learner,'fit',fit), patch.object(nested.learner,'predict',predict):
            chosen, diagnostics = nested.select(rows,folds,0)
        self.assertEqual(chosen,list(nested.CONFIGS[0]))
        self.assertEqual(len(seen),72)
        self.assertEqual(len(diagnostics),18)
