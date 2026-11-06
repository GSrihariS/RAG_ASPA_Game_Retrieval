# Data Format

## Source reviews

`all_reviews.json`, each game's `reviews.json`, and `processing_sample_50/sample_reviews.json` contain a `metadata` object and a `reviews` array. Each review has these 16 fields:

| Field | Type | Meaning |
|---|---|---|
| `review_id` | string | Steam recommendation ID; unique together with appid. |
| `appid` | integer | Steam application ID. |
| `game_name` | string | Game name. |
| `review_text` | string | Original review body from Steam. |
| `language` | string | Steam language field. |
| `steam_recommended` | boolean | Overall Steam recommendation. |
| `created_at_utc` | string or null | ISO 8601 creation timestamp with timezone. |
| `updated_at_utc` | string or null | ISO 8601 update timestamp with timezone. |
| `playtime_at_review_minutes` | integer or null | Playtime when the review was written, in minutes. |
| `helpful_votes` | integer | Steam votes_up. |
| `weighted_vote_score` | string or null | Steam weighted helpfulness score, preserving API precision. |
| `funny_votes` | integer | Steam votes_funny. |
| `steam_purchase` | boolean | Steam purchase flag. |
| `received_for_free` | boolean | Free-copy flag. |
| `written_during_early_access` | boolean | Early Access flag. |
| `source_url` | string | Steam source review URL. |

Example source record:

```json
{
  "review_id": "233731833",
  "appid": 1030300,
  "game_name": "Hollow Knight: Silksong",
  "review_text": "the game is great and deserve to be overwhelmingly positive",
  "language": "english",
  "steam_recommended": true,
  "created_at_utc": "2026-08-26T09:59:03+00:00",
  "updated_at_utc": "2026-08-26T09:59:03+00:00",
  "playtime_at_review_minutes": 18326,
  "helpful_votes": 99,
  "weighted_vote_score": "0.809920787811279297",
  "funny_votes": 5,
  "steam_purchase": false,
  "received_for_free": true,
  "written_during_early_access": false,
  "source_url": "https://steamcommunity.com/profiles/76561199438545916/recommended/1030300/"
}
```

`raw_responses.json` stores a `metadata` object and a `pages` array containing the collected API response snapshots.

## Processed documents

The files in `processed/` use JSON Lines: one JSON object per line. The 50-review examples are stored separately in `processing_sample_50/processed/`.

`clean_reviews.jsonl` contains every source record plus:

| Field | Type | Meaning |
|---|---|---|
| `cleaned_text` | string | Formatting-cleaned text, including all original language sections |
| `cleaning_actions` | string array | Applied operations, such as `inline_tags`, `checkbox_templates`, or `links` |
| `extracted_urls` | string array | URL destinations extracted from the review |

`filtered_reviews.jsonl`, `excluded_reviews.jsonl`, and `review_candidates.jsonl` add:

| Field | Type | Meaning |
|---|---|---|
| `retrieval_text` | string | Retained English text, or retained short text with language undetermined; empty for unresolved or non-English records |
| `quality_check` | object | Decision, language evidence, selected spans, and duplicate reference |

`quality_check` contains:

| Field | Type | Meaning |
|---|---|---|
| `decision` | string | `keep` or `exclude` |
| `reason` | string | Processing reason, e.g. `english`, `english_sections_retained`, `non_english`, or `duplicate_text` |
| `source_language` | string | Language assigned to the full cleaned review by the model |
| `language_score` | number | Normalized model score for that assignment |
| `detected_language` | string | Language of retained text; `und` means undetermined |
| `detected_languages` | string array | Languages detected across the body and its lines; `non_en` marks strong evidence of non-Latin characters |
| `sections` | object array | Line-level evidence: `char_start`, `char_end`, `language`, `score`, plus optional `marker`, `inferred`, and `mixed_sentence` flags |
| `selected_spans` | object array | Selected ranges in `cleaned_text`, with inclusive `char_start` and exclusive `char_end` |
| `duplicate_of` | string, optional | Canonical document ID for an archived duplicate |
| `original_reason` | string, optional | Language-check reason before an unresolved case was archived |
| `language_exclusion_basis` | string, optional | `not_confirmed_english` for unresolved cases archived in the `non_english` category |

Selected spans are joined with a blank line to form `retrieval_text`. Source fields remain available in every processed document. Archived duplicates may still have `retrieval_text`; their decision controls inclusion in the chunk file.

The `non_english` exclusion category includes detected non-English reviews and unresolved English-language cases. `review_candidates.jsonl` is empty under the current policy.

## Retrieval chunks

`processed/chunks.jsonl` contains:

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `steam:APPID:REVIEW_ID:chunk:NNN` |
| `document_id` | string | `steam:APPID:REVIEW_ID`, linking back to the retained review |
| `text` | string | The passage used for retrieval |
| `source` | string | `steam` |
| `title` | string | Game name and review ID |
| `metadata` | object | Source fields, cleaning provenance, language action, and chunk offsets |

Chunk metadata contains all source fields except `review_text`, plus `cleaning_actions`, `extracted_urls`, `detected_language`, `language_action`, `chunk_index`, `chunk_count`, `word_count`, `char_start`, `char_end`, `offset_text_field`, and `overlap_word_count`.

`chunk_index` starts at 1. Character offsets start at 0 and count Unicode code points in `retrieval_text`. The chunk text runs from `char_start` inclusive to `char_end` exclusive. `offset_text_field` is `retrieval_text`. `overlap_word_count` counts words repeated from the preceding chunk.

Example chunk:

```json
{
  "id": "steam:1030300:233731833:chunk:001",
  "document_id": "steam:1030300:233731833",
  "text": "the game is great and deserve to be overwhelmingly positive",
  "source": "steam",
  "title": "Hollow Knight: Silksong \u2014 review 233731833",
  "metadata": {
    "review_id": "233731833",
    "appid": 1030300,
    "game_name": "Hollow Knight: Silksong",
    "language": "english",
    "steam_recommended": true,
    "created_at_utc": "2026-08-26T09:59:03+00:00",
    "updated_at_utc": "2026-08-26T09:59:03+00:00",
    "playtime_at_review_minutes": 18326,
    "helpful_votes": 99,
    "weighted_vote_score": "0.809920787811279297",
    "funny_votes": 5,
    "steam_purchase": false,
    "received_for_free": true,
    "written_during_early_access": false,
    "source_url": "https://steamcommunity.com/profiles/76561199438545916/recommended/1030300/",
    "cleaning_actions": [],
    "extracted_urls": [],
    "detected_language": "und",
    "language_action": "language_unresolved_short_text",
    "chunk_index": 1,
    "chunk_count": 1,
    "word_count": 10,
    "char_start": 0,
    "char_end": 59,
    "offset_text_field": "retrieval_text",
    "overlap_word_count": 0
  }
}
```

## Reports and catalog

`processing_report.json` contains counts, decision reasons, source and retained recommendation distributions, word totals, per-game statistics, chunk settings, and validation results. `analysis_summary.json` summarizes the 10,000 collected source reviews and the retained corpus, including word types and aspect keyword matches. `collection_manifest.json` records collection parameters, per-game windows, and supplemental sampling runs; `games.json` stores the game catalog.
