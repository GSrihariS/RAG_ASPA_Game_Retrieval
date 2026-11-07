# Knowledge-base construction

Run these commands from `code/` after installing `requirements.txt`.

## Collect reviews

```bash
python -m data_pipeline.collect_steam_reviews
```

Requests 500 English reviews per game for the 20 games in the script, using helpfulness order and
`day_range=365`, both recommendation outcomes, and all purchase types. The default output is
`data/knowledge_base_all_365_500/`, containing `all_reviews.json`, per-game records, raw API responses,
and a collection manifest. Use `--output` to choose another directory.

## Process reviews

```bash
python -m data_pipeline.process_steam_reviews
```

The default input is `data/knowledge_base/all_reviews.json`; the output directory is
`data/knowledge_base/processed/`.

Input can be a JSON object with a `reviews` array, a JSON array, or JSONL. Each review contains
`review_id`, `appid`, `game_name`, `review_text`, and `steam_recommended`, plus its source metadata.
See [DATA_FORMAT.md](../../data/knowledge_base/DATA_FORMAT.md) for the fields.

To process the newly collected reviews, set the input and output explicitly:

```bash
python -m data_pipeline.process_steam_reviews --input ../data/knowledge_base_all_365_500/all_reviews.json --output ../data/knowledge_base_all_365_500/processed
```

The pipeline cleans Steam formatting and checkbox templates, checks language, and removes duplicate
review texts within each game. Reviews up to 150 words stay whole; longer reviews target 120 words
per passage, with optional overlap of one sentence of up to 30 words.

Main output files:

| File | Content |
|---|---|
| `clean_reviews.jsonl` | All source reviews with cleaned text |
| `filtered_reviews.jsonl` | Retained reviews and their retrieval text |
| `excluded_reviews.jsonl` | Excluded reviews with their reasons |
| `chunks.jsonl` | Passages with IDs, source metadata, and character offsets |
| `processing_report.json` | Corpus counts, processing settings, and validation checks |

## Agreement calculation

```bash
python -m data_pipeline.calculate_iaa
```

Reads `data/evaluation_dataset/steam_annotations_iaa.json` and writes `iaa_report.json` in the same
folder. Each review record contains `annotator_1` and `annotator_2` alongside its final labels.
The eight-character codes use the shared `aspect_order` and `sentiment_codes`; `=` refers to the first annotator's codes.
The compact codes include the data team's retrospectively supplied differences between two review
passes. The script reports label agreement, exact passage agreement, and Cohen's kappa.

The reported two-pass exact passage agreement is **98.2% (982/1,000 passages)**.
Full results are in [iaa_report.json](../../data/evaluation_dataset/iaa_report.json).
