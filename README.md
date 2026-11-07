```bash
streamlit run app.py
```

**Command-line search:**

```bash
python -m retrieval.query_sparse "How is the soundtrack?" --game "Hollow Knight"
python -m retrieval.query_dense "How is the soundtrack?" --game "Hollow Knight"
python -m retrieval.query_hybrid "How is the soundtrack?" --game "Hollow Knight"
```

**Rebuild the indexes.** `data.zip` already contains them, so this is only needed if the chunks change:

```bash
python -m retrieval.build_sparse_index
python -m retrieval.build_dense_index
```

**Retrieval evaluation.** About 40 minutes with the reranker on an RTX 3070 Ti Laptop GPU; details and
results are in [eval/README.md](code/eval/README.md):

```bash
python eval/evaluate_annotated.py
```

**Annotation set tools:**

```bash
python eval/dataset_stats.py
python eval/export_eval_xls.py
```

## Knowledge-base construction

`data.zip` already contains the built knowledge base, so these steps are only needed to rebuild it. Run them
from `code/`; [code/data_pipeline/README.md](code/data_pipeline/README.md) has the details and output files.

```bash
python -m data_pipeline.collect_steam_reviews
python -m data_pipeline.process_steam_reviews
```

Collection calls the Steam API and writes to a new folder, `data/knowledge_base_all_365_500/`. Processing reads
`data/knowledge_base/all_reviews.json` and overwrites `data/knowledge_base/processed/`. If the chunks change,
rebuild the indexes as well.

**Annotation agreement.** This writes `data/evaluation_dataset/iaa_report.json`:

```bash
python -m data_pipeline.calculate_iaa
```

## Downstream task and generation

The downstream task is evidence-grounded RAG summarization: answer a question from retrieved Steam reviews,
with citations to the supporting passages. The module is in `code/generation/rag_summary/` and supports
few-shot prompting and query-aware context compression. Generation and ROUGE scoring use the Python standard
library and require no additional packages. Run the commands below from `code/`.

**Generate an answer in the UI.** Set an API key for an OpenAI-compatible service, start the UI, search,
then click **Generate summary**. On Windows PowerShell, use `$env:GENERATION_API_KEY = "your-key"`.

```bash
export GENERATION_API_KEY=your-key
streamlit run app.py
```

The app defaults to `https://api.deepseek.com` and `deepseek-v4-pro`. Set `GENERATION_BASE_URL` and
`GENERATION_MODEL` to use another endpoint or model. Generated answers are saved under
`data/generation_results/rag_summary/`.

**Generation benchmark and experiment.** The benchmark has 100 questions, each with 10 fixed
`hybrid_rerank` review passages and a human-reviewed English reference summary. The frozen split uses
20 development questions and 80 test questions. Two development questions (`q06` and `q24`) provide
the few-shot examples.

The experiment compares four methods:

| Method | Few-shot examples | Context compression |
|---|---|---|
| `baseline` | No | No |
| `few_shot` | Yes | No |
| `compressed` | No | Yes |
| `combined` | Yes | Yes |

The five required data files are stored directly in `data/evaluation_dataset/`:

```text
rag_summary_benchmark.jsonl
rag_summary_approved_references.jsonl
rag_summary_reference_contexts.jsonl
rag_summary_split.json
rag_summary_few_shot_examples.json
```

**Run the experiment webpage.** Start the local server, then enter the API key, API endpoint and model
in the browser. The webpage displays progress and exports a ZIP of the results.

```bash
python generation/rag_summary/launch_web.py
```

For the final experiment configuration, select the test split, 80 questions, all four methods, one repeat,
compression ratio 0.75, concurrency 20 and two retries. Each failed retryable request is attempted up to
three times in total. New web runs are saved under `data/generation_results/rag_summary/`.

**Final results.** The `deepseek-v4-pro` run completed 315 of 320 tasks. Few-shot prompting achieved the
highest ROUGE-1/2/L F1 scores: **29.42 / 10.38 / 20.54**, compared with **28.41 / 8.63 / 19.05** for
baseline (percentages). Compression reduced mean input tokens by **9.4%** over the 78 questions completed
by both compression and baseline, with ROUGE-2 and ROUGE-L close to baseline.

The final outputs are in [data/generation_results/rouge_results/](data/generation_results/rouge_results/).
Earlier experiment outputs are retained in
[data/generation_results/llm_judge_results/](data/generation_results/llm_judge_results/).
The full scores, paired comparisons and file descriptions are in [data/README.md](data/README.md).

**Reproduce the final scores.** This validates the saved evidence and recomputes ROUGE against the reviewed
English references without an API key or evaluation model. Use a new output folder:

```bash
python generation/rag_summary/evaluate_generation.py ../data/generation_results/rouge_results --output ../data/generation_results/rouge_rescored
```

The generation interface is defined in
[rag_generator.py](code/generation/rag_summary/rag_generator.py), and the prompts are in
[prompts/](code/generation/rag_summary/prompts/).
