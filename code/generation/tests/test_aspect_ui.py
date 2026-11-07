"""Isolated Streamlit ABSA panel smoke test, with Retrieval imports stubbed.

This does not validate the dense index, reranker, or live retrieval pipeline.
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from generation.aspect_analysis import DEFAULT_MODEL, RESULTS_DIR


@unittest.skipUnless(importlib.util.find_spec('streamlit'), 'Streamlit not installed')
class AspectUITests(unittest.TestCase):
    def test_panel_renders_real_checkpoint_and_json_download(self):
        if not DEFAULT_MODEL.exists():
            self.skipTest('Train checkpoint first')
        from streamlit.testing.v1 import AppTest
        modules = {}
        for name, symbol in [('retrieval.hybrid_retriever', 'HybridRetriever'), ('retrieval.reranker', 'Reranker'),
                             ('retrieval.query_expansion', 'expand_query')]:
            module = types.ModuleType(name)
            setattr(module, symbol, lambda *args, **kwargs: None)
            modules[name] = module
        code = f'''import json
from pathlib import Path
from generation.aspect_ui import render_aspect_analysis
payload=json.loads(Path({str(RESULTS_DIR / 'aspect_results/example_retrieval.json')!r}).read_text())
result=render_aspect_analysis(payload['results'],payload['query'])
assert result['input_review_count']==5
'''
        with patch.dict(sys.modules, modules):
            app = AppTest.from_string(code).run(timeout=30)
        self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])
        self.assertEqual(len(app.dataframe), 1)
        self.assertEqual(len(app.get('download_button')), 1)


if __name__ == '__main__':
    unittest.main()
