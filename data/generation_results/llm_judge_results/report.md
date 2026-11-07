# Structured fact selection results

Scoring uses exact ID matching; no evaluator model is called.
All eight aspect slots per review are visible to generation; gold labels and reference sets are not.
P/R/F1 concern review-aspect selection. Natural-language summary entailment is not scored.
Condition candidates are unreviewed; condition retention remains unavailable.
C/D self-verification uses the generator model and is part of generation, not the final scorer.

| Method | Completed | Failed | Precision | Recall | F1 | Unit recall | Contrast coverage | Latency s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| improved | 100 | 0 | 0.84325 | 0.6880733464066797 | 0.7320547753421381 | 0.8813612313612313 | 0.5454545454545454 | 4.806933009999999 |
| verify_delete | 99 | 1 | 0.856547619047619 | 0.6778933368219082 | 0.7274735645699821 | 0.880150631681244 | 0.5454545454545454 | 11.764731568686875 |
| baseline | 100 | 0 | 0.8141666666666667 | 0.7155954034741914 | 0.7348673700887792 | 0.8883597883597883 | 0.5227272727272727 | 3.1240646 |
| verify_revise | 99 | 1 | 0.8453703703703703 | 0.6869312376965439 | 0.7327624933282986 | 0.880150631681244 | 0.5454545454545454 | 12.042440570707072 |

All metric means disclose valid counts in summary.csv. Failed tasks are listed separately.
B/C/D share a draft; logical latency, usage and cost include one draft per arm.
