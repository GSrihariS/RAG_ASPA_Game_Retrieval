# ABSA Team Handoff

The ABSA contribution lives in `code/generation/`. Models, evaluation outputs and real retrieval examples are under `data/generation_results/absa/`.

The [combined Generation report](docs/generation_report.md) places the Overview before Section 4.1 and the summarization results in Section 4.2. Use the [standalone Section 4.1](docs/aspect_report.md) when inserting ABSA into the team paper. The [English presentation guide](docs/PRESENTATION_GUIDE.md) contains the speaking notes and live demonstration.

Run `streamlit run app.py` from `code/`. Choose the Monster Hunter Wilds graphics and performance query, then switch between **Previous baseline** and **Optimized**. The end-to-end Micro-F1 comparison is 0.6719 to 0.7748 on the reused test split. The report explains the weaker Neutral result and the explicit cue override.

For integration, call `generation.aspect_analysis.AspectAnalyzer.load().analyze(hits, query=query)` and include the returned payload under `aspect_analysis`. Preserve `chunk_id` and `metadata.document_id` for citations and review deduplication.
