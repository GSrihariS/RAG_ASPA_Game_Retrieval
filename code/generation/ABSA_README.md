# Aspect-based sentiment analysis (ABSA)

The ABSA component labels aspect mentions in ranked Steam review passages and returns review-level sentiment distributions and source excerpts. The Streamlit app displays those results and includes them under `aspect_analysis` in the search export.

Run the following commands from `code/` after installing `requirements.txt` and unpacking the team's data package:

```bash
streamlit run app.py
python -m unittest discover -s generation/tests -v
python -m generation.verify_live_aspect
```

In the app, select a query and switch **Aspect model** between **Previous baseline** and **Optimized** to compare predictions for the same retrieved reviews.

To analyze a saved search export:

```bash
python -m generation.aspect_analysis --input ../data/generation_results/absa/aspect_live_runs/monster_hunter_graphics_performance/search_results.json
```

Run `python -m generation.evaluate_aspect` to regenerate the model and evaluation results in `data/generation_results/absa/`. This overwrites generated checkpoints. Use `--legacy-baselines` to run the original baseline evaluation. To regenerate the English report and figure, install `generation/requirements-report.txt` and run `python -m generation.build_aspect_report`.

The summarization component can use the same ranked passages. For source references, preserve `chunk_id` and the review ID in `metadata.document_id`.

```python
from generation.aspect_analysis import AspectAnalyzer

analyzer = AspectAnalyzer.load()
aspect_analysis = analyzer.analyze(hits, query=query)
```

The output exposes aspect counts, sentiment ratios, passage IDs and exact excerpt offsets. An explicit cue override preserves the classifier's original label and scores.

- [English Section 4.1](docs/aspect_report.md)
- [Generation overview paragraph](docs/generation_overview.md)
- [Presentation guide](docs/PRESENTATION_GUIDE.md)
- [Team handoff](TEAM_HANDOFF.md)
- [ABSA evaluation and examples](../../data/README.md#aspect-based-sentiment-analysis)
