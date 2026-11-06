# Review Processing

The full collection is processed with formatting cleanup, language selection, duplicate handling, and chunking. Results are in `processed/`. The 50-review walkthrough is in `processing_logic.html`, with its source records and results under `processing_sample_50/`.


## Formatting

Steam headings and lists become plain-text paragraph and list boundaries. Font and spoiler tags are removed. Struck-through text becomes `[Struck-through: ...]` to retain its meaning. Link labels remain in text, URL destinations become `<URL>`, and the extracted addresses are saved in `extracted_urls`.

Line endings and repeated whitespace are normalized. Symbol art keeps its line structure and indentation. Short comments, emojis, punctuation, negation, and censor hearts remain in the data.

### Checkbox templates

Checkbox templates contain decorated headings such as `---{ Graphics }---` followed by options. A template needs at least two groups with at least two options each. Cleaning keeps the section heading and selected `☑` / `☒` options, including multiple selections and additional prose. Groups without a selected option remain intact. The known template-author credit is saved as a URL.

```text
---{ Graphics }---       → Graphics: Beautiful
☐ Bad
☑ Beautiful
☐ Masterpiece
```

Examples `s003` and `s006` show the full template conversion.

## Language selection

Language detection checks the complete cleaned review and substantive lines, with a normalized score threshold of 0.9. The detection probe normalizes Unicode typography and removes symbols; stored text retains its content. Explicit section markers and adjacent passages help assign short headings.

- English reviews retain their full cleaned text.
- Clearly separated bilingual reviews retain their English sections in `retrieval_text`; all sections remain in `cleaned_text` and `review_text`.
- Detected non-English reviews and unresolved review cases are stored in `excluded_reviews.jsonl` under the `non_english` category.
- Unresolved cases retain their original language-check reason in `original_reason` and are marked `not_confirmed_english` in `language_exclusion_basis`.
- Text with fewer than 30 letters remains available with language `und`; Latin-majority text with fewer than 12 words also remains undetermined. Longer non-Latin text is checked even when its word count is small.

Examples `s004`, `s012`, and `s013` show English extraction. Example `s035` shows a non-English record being archived.

## Duplicates

Within each game, duplicate detection compares retained text after Unicode NFC normalization, case folding, and whitespace normalization. The review with the most helpful votes is kept, using input order to break ties. Archived records link to the retained document through `duplicate_of`. Examples `s039`–`s042` show duplicate handling.

## Chunking

Reviews up to 150 words stay in one chunk. Longer reviews prefer paragraph endings, followed by sentence endings, near a target of 120 words. The preferred range is 100–150 words, and the final remainder can be shorter. Oversized sentences use a word boundary. Headings stay with following text where the size limit permits.

An adjacent chunk may repeat one complete sentence from the previous chunk, up to 30 words, when the result still fits within 150 words. Each chunk contains text from one review. Word counts use Unicode letters and numbers, with internal apostrophes retained.

Validation checks coverage of retained text and chunk size limits. Chunk offsets point into `retrieval_text`; language selection offsets point into `cleaned_text`.

The results include five JSONL files and one processing report. The chunks are stored in `chunks.jsonl`, and complete retained documents are available in `filtered_reviews.jsonl`.
