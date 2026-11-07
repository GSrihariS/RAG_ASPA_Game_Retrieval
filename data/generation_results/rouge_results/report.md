# ROUGE summarization results

ROUGE compares generated English summaries with human-reviewed reference answers.
Citation ID markers are removed; text is lowercased into English alphanumeric tokens without stemming.
ROUGE-L uses whole-answer LCS. Scores in JSON/CSV are 0–1; this table shows F1 percentages.
All nine precision/recall/F1 metrics and their valid counts are in summary.csv.
Each method generates independently; transient or invalid responses may be retried. No self-check or evaluator is used.
Per-task latency includes retry attempts and backoff; token totals include all reported attempt usage.

| Method | Completed | Failed | ROUGE-1 F1 | ROUGE-2 F1 | ROUGE-L F1 | Input tokens | Latency s | Text retained |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 79 | 1 | 28.41 | 8.63 | 19.05 | 3276.8734177215188 | 3.9648440253164554 | 1.0 |
| few_shot | 79 | 1 | 29.42 | 10.38 | 20.54 | 4667.0 | 4.448291670886077 | 1.0 |
| compressed | 78 | 2 | 27.63 | 9.04 | 19.15 | 2972.0897435897436 | 4.004229064102564 | 0.7478775276819395 |
| combined | 79 | 1 | 28.97 | 10.23 | 20.39 | 4508.2531645569625 | 4.609231341772152 | 0.7478072697376658 |

## Paired comparisons

ROUGE differences use percentage points; other metrics retain their original units.
| After - before | Metric | Queries | Delta | Bootstrap 95% CI |
|---|---|---:|---:|---:|
| few_shot - baseline | rouge1_f1 | 79 | 1.00509 | [-0.152594, 2.17526] |
| few_shot - baseline | rouge2_f1 | 79 | 1.74832 | [0.951641, 2.5704] |
| few_shot - baseline | rougeL_f1 | 79 | 1.4895 | [0.485179, 2.50271] |
| few_shot - baseline | prompt_tokens | 79 | 1390.13 | [1310.38, 1430] |
| few_shot - baseline | latency_seconds | 79 | 0.483448 | [0.231578, 0.711217] |
| compressed - baseline | rouge1_f1 | 78 | -0.745563 | [-2.20726, 0.758279] |
| compressed - baseline | rouge2_f1 | 78 | 0.395212 | [-0.619645, 1.50137] |
| compressed - baseline | rougeL_f1 | 78 | 0.118517 | [-1.1734, 1.55499] |
| compressed - baseline | prompt_tokens | 78 | -308.5 | [-403.372, -252.013] |
| compressed - baseline | latency_seconds | 78 | 0.0507926 | [-0.164879, 0.247249] |
| combined - baseline | rouge1_f1 | 79 | 0.551889 | [-0.801796, 1.93484] |
| combined - baseline | rouge2_f1 | 79 | 1.5947 | [0.587922, 2.60499] |
| combined - baseline | rougeL_f1 | 79 | 1.33974 | [0.145306, 2.53065] |
| combined - baseline | prompt_tokens | 79 | 1231.38 | [1047.82, 1491.76] |
| combined - baseline | latency_seconds | 79 | 0.644387 | [0.330994, 0.985269] |
| combined - few_shot | rouge1_f1 | 79 | -0.453203 | [-1.96727, 1.08167] |
| combined - few_shot | rouge2_f1 | 79 | -0.153619 | [-1.14108, 0.87012] |
| combined - few_shot | rougeL_f1 | 79 | -0.149756 | [-1.33118, 1.07285] |
| combined - few_shot | prompt_tokens | 79 | -158.747 | [-282.241, 70.3671] |
| combined - few_shot | latency_seconds | 79 | 0.16094 | [-0.0873453, 0.470384] |
| combined - compressed | rouge1_f1 | 78 | 1.29385 | [0.11493, 2.44617] |
| combined - compressed | rouge2_f1 | 78 | 1.20365 | [0.314418, 2.08019] |
| combined - compressed | rougeL_f1 | 78 | 1.19542 | [-0.0447787, 2.39373] |
| combined - compressed | prompt_tokens | 78 | 1541.54 | [1430, 1764.62] |
| combined - compressed | latency_seconds | 78 | 0.621007 | [0.357039, 0.928695] |

## Factorial interactions

Combined - few-shot - compression + baseline; ROUGE differences in percentage points.
| Metric | Queries | Interaction (pp) | Bootstrap 95% CI (pp) |
|---|---:|---:|---:|
| rouge1_f1 | 78 | 0.305 | [-1.345, 1.913] |
| rouge2_f1 | 78 | -0.553 | [-1.615, 0.534] |
| rougeL_f1 | 78 | -0.277 | [-1.843, 1.201] |

Bootstrap sampling uses questions as units, keeping repetitions together.
The split, demonstrations, full and actual evidence, compression spans and settings are saved for each new run.

## Execution

Concurrency: 20; maximum retries: 2.
Generation wall time: 73.789 s; completed answers/s: 4.269.
Each saved row contains all attempts and request totals, including exhausted failures.
