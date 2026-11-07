"""Clean, check, deduplicate, and chunk Steam reviews."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from langid.langid import LanguageIdentifier, model

from paths import CHUNKS_PATH, KNOWLEDGE_BASE_DIR

WORD_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")
PARAGRAPH_RE = re.compile(r"\S[\s\S]*?(?=\n[ \t]*\n|\Z)")
SENTENCE_END_RE = re.compile(r"[.!?]+[\"'”’)\]]*(?=\s|$)")
STRUCK_RE = re.compile(r"\[Struck-through:[^\]]*\]")


BB_RE = re.compile(r"\[/?(?:h[1-3]|b|i|u|strike|spoiler|list|olist|\*|hr|url)(?:=[^\]\n]*)?\]", re.I)

URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\[\]]+", re.I)

ANCHOR_RE = re.compile(r"\[url=([^\]\n]+)\](.*?)\[/url\]", re.I | re.S)

STRIKE_RE = re.compile(r"\[strike\](.*?)\[/strike\]", re.I | re.S)

CHECKBOX_HEADER_RE = re.compile(
    r"^[ \t]*[-=]{2,}[ \t]*[{\[][ \t]*(.+?)[ \t]*[}\]][ \t]*[-=]{2,}[ \t]*$",
    re.M,
)

CHECKBOX_OPTION_RE = re.compile(r"^[ \t]*([☐☑☒])\ufe0f?[ \t]*(\S.*?)[ \t]*$")

TEMPLATE_CREDIT_URL = "https://vojtastruhar.github.io/steam-review-template"

def art_line(line: str) -> bool:
    visible = [c for c in line if not c.isspace()]
    return len(visible) >= 4 and sum(c.isalnum() for c in visible) / len(visible) < 0.2

def split_url_suffix(value: str) -> tuple[str, str]:
    suffix = ""
    while value and value[-1] in ".,;:!?\"'":
        suffix = value[-1] + suffix
        value = value[:-1]
    for opening, closing in (("(", ")"), ("{", "}")):
        while value.endswith(closing) and value.count(closing) > value.count(opening):
            suffix = closing + suffix
            value = value[:-1]
    return value, suffix

def clean_checkbox_templates(text: str) -> tuple[str, list[str]]:
    headings = list(CHECKBOX_HEADER_RE.finditer(text))
    sections = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[heading.end():end]
        options = []
        for line in body.splitlines():
            option = CHECKBOX_OPTION_RE.fullmatch(line)
            if option:
                options.append((option.group(1), option.group(2)))
        sections.append((heading, body, options))

    # Two option groups distinguish a review template from an ordinary checklist.
    if sum(len(options) >= 2 for _, _, options in sections) < 2:
        return text, []

    parts = [text[:headings[0].start()]]
    credit_urls = []
    for heading, body, options in sections:
        selected = [value for mark, value in options if mark != "☐"]
        if not selected:
            parts.append(heading.group(0) + body)
            continue

        notes = []
        for line in body.splitlines(keepends=True):
            if not CHECKBOX_OPTION_RE.fullmatch(line.rstrip("\r\n")):
                notes.append(line)
        notes_text = "".join(notes).strip("\n")
        title = heading.group(1).strip()
        if title.casefold() == "author" and selected == [TEMPLATE_CREDIT_URL]:
            credit_urls.append(TEMPLATE_CREDIT_URL)
        else:
            parts.append(f"{title}: {'; '.join(selected)}\n\n")
        if notes_text:
            parts.append(notes_text + "\n\n")

    return "".join(parts), credit_urls

def clean_formatting(original: str) -> tuple[str, list[str], list[str]]:
    text = original
    actions: list[str] = []
    urls: list[str] = []

    def apply(action, transform):
        nonlocal text
        updated = transform(text)
        if updated != text:
            actions.append(action)
        text = updated

    apply("line_endings", lambda s: s.replace("\r\n", "\n").replace("\r", "\n"))

    def anchor(match):
        destination, label = match.group(1).strip(), match.group(2)
        urls.append(destination)
        if URL_RE.fullmatch(label.strip()):
            return "<URL>"
        return label + " <URL>"

    # Keep the link text.
    apply("links", lambda s: ANCHOR_RE.sub(anchor, s))
    apply("strikethrough", lambda s: STRIKE_RE.sub(lambda m: "[Struck-through: " + m.group(1) + "]", s))

    def block_cleanup(s):
        s = re.sub(r"\[/?h[1-3]\]", "\n\n", s, flags=re.I)
        s = re.sub(r"\[/?(?:list|olist)\]", "\n\n", s, flags=re.I)
        s = re.sub(r"\[\*\]", "\n- ", s)
        return re.sub(r"\[hr\]", "\n\n---\n\n", s, flags=re.I)

    apply("block_tags", block_cleanup)
    apply("inline_tags", lambda s: re.sub(r"\[/?(?:b|i|u|spoiler|url)\]", "", s, flags=re.I))

    updated, credit_urls = clean_checkbox_templates(text)
    if updated != text:
        actions.append("checkbox_templates")
    text = updated
    urls.extend(credit_urls)

    def naked_link(match):
        destination, punctuation = split_url_suffix(match.group(0))
        urls.append(destination)
        return "<URL>" + punctuation

    apply("links", lambda s: URL_RE.sub(naked_link, s))

    def spaces(s):
        lines = []
        for line in s.split("\n"):
            if art_line(line):
                lines.append(line.rstrip())
            else:
                lines.append(re.sub(r"[ \t\u00a0]+", " ", line).strip())
        return "\n".join(lines)

    apply("horizontal_spaces", spaces)
    apply("blank_lines", lambda s: re.sub(r"\n{3,}", "\n\n", s).strip("\n"))
    return text, list(dict.fromkeys(actions)), list(dict.fromkeys(urls))

def word_count(text):
    return len(WORD_RE.findall(text))

def sentence_spans(text):
    spans = []
    for paragraph in PARAGRAPH_RE.finditer(text):
        start = paragraph.start()
        for ending in SENTENCE_END_RE.finditer(text, paragraph.start(), paragraph.end()):
            end = ending.end()
            line_start = max(paragraph.start(), text.rfind("\n", paragraph.start(), ending.start()) + 1)
            if re.fullmatch(r"[ \t]*\d+[.)]", text[line_start:end]):
                continue
            while start < end and text[start].isspace():
                start += 1
            spans.append((start, end))
            start = end
    return spans

def is_heading(text):
    return (
        "\n" not in text
        and 1 <= word_count(text) <= 12
        and any(char.isalpha() for char in text)
        and not re.search(r"[.!?][\"'”’)\]]*$", text)
        and not text.lstrip().startswith(("- ", "• ", "☐", "☑"))
    )

def split_review(text, min_words=100, target_words=120, max_words=150, overlap_words=30):
    if word_count(text) <= max_words:
        return [(0, len(text), 0)]

    paragraph_matches = list(PARAGRAPH_RE.finditer(text))
    paragraphs = [match.end() for match in paragraph_matches]
    sentences = sentence_spans(text)
    protected = [(match.start(), match.end()) for match in STRUCK_RE.finditer(text)]
    for paragraph, following in zip(paragraph_matches, paragraph_matches[1:]):
        if is_heading(paragraph.group()):
            protected.append((paragraph.start(), following.start()))
    bases = []
    start = 0
    while start < len(text):
        remaining = list(WORD_RE.finditer(text, start))
        if len(remaining) <= max_words:
            bases.append((start, len(text)))
            break
        hard_end = remaining[max_words].start()

        def suitable(end):
            if not start < end <= hard_end:
                return False
            if any(left < end < right for left, right in protected):
                return False
            return min_words <= word_count(text[start:end]) <= max_words

        choices = [end for end in paragraphs if suitable(end)]
        if not choices:
            choices = [end for _, end in sentences if suitable(end)]
        if choices:
            end = min(choices, key=lambda value: (abs(word_count(text[start:value]) - target_words), value))
        else:
            end = hard_end
            for left, right in protected:
                if start < left < end < right:
                    end = left
                    break
        while end > start and text[end - 1].isspace():
            end -= 1
        bases.append((start, end))
        start = end
        while start < len(text) and text[start].isspace():
            start += 1

    chunks = []
    for index, (start, end) in enumerate(bases):
        overlap = 0
        if index:
            previous_start, previous_end = bases[index - 1]
            # Reuse a complete final sentence when it fits.
            for sentence_start, sentence_end in reversed(sentences):
                if sentence_start < previous_start or sentence_end > previous_end:
                    continue
                if text[sentence_end:previous_end].strip():
                    continue
                count = word_count(text[sentence_start:sentence_end])
                if 0 < count <= overlap_words and word_count(text[sentence_start:end]) <= max_words:
                    start = sentence_start
                    overlap = count
                break
        chunks.append((start, end, overlap))
    return chunks

def validate_spans(text, spans, max_words):
    covered_until = 0
    for start, end, _ in spans:
        assert 0 <= start <= end <= len(text)
        assert not text[covered_until:start].strip(), "Uncovered review text"
        assert word_count(text[start:end]) <= max_words, "Chunk exceeds word limit"
        covered_until = max(covered_until, end)
    assert not text[covered_until:].strip(), "Missing review ending"


def document_id(review):
    return f"steam:{review['appid']}:{review['review_id']}"


def language_sections(text, identifier, confidence):
    def classify(value):
        value = unicodedata.normalize("NFKC", value)
        probe = "".join(" " if unicodedata.category(char).startswith("S") else char for char in value)
        return identifier.classify(probe)

    whole_language, whole_score = classify(text)
    result = {
        "source_language": whole_language,
        "language_score": round(float(whole_score), 6),
        "detected_language": "und",
        "detected_languages": [],
        "sections": [],
        "selected_spans": [],
    }
    letters = [char for char in unicodedata.normalize("NFKC", text) if char.isalpha()]
    non_latin = sum("LATIN" not in unicodedata.name(char, "") for char in letters)
    if len(letters) < 30 or (word_count(text) < 12 and non_latin <= len(letters) / 2):
        result["selected_spans"] = [{"char_start": 0, "char_end": len(text)}]
        return "keep", "language_unresolved_short_text", text, result

    lines = []
    offset = 0
    marker = None
    marker_languages = {"ENG": "en", "EN": "en", "ENGLISH": "en", "UA": "uk", "UK": "uk", "RU": "ru", "DE": "de"}
    for line in text.splitlines(keepends=True):
        value = line.strip()
        start = offset + len(line) - len(line.lstrip())
        end = offset + len(line.rstrip())
        offset += len(line)
        if not value:
            continue
        entry = {"char_start": start, "char_end": end, "language": None, "score": None}
        match = re.fullmatch(r"(ENG|EN|ENGLISH|UA|UK|RU|DE):", value, re.I)
        if match:
            marker = marker_languages[match.group(1).upper()]
            entry.update(language=marker, marker=True)
        else:
            letters = [char for char in unicodedata.normalize("NFKC", value) if char.isalpha()]
            foreign_letters = sum("LATIN" not in unicodedata.name(char, "") for char in letters)
            if len(letters) >= 30 or word_count(value) >= 8 or foreign_letters >= 4:
                language, score = classify(value)
                entry["score"] = round(float(score), 6)
                if score >= confidence:
                    entry["language"] = language
                elif foreign_letters > len(letters) / 2:
                    entry["language"] = "non_en"
                if foreign_letters >= 15 and len(letters) - foreign_letters >= 30:
                    # Names in another script can be checked along with sentence mixing.
                    sentence_languages = set()
                    for sentence in re.split(r"(?<=[.!?])\s+", value):
                        if word_count(sentence) >= 8:
                            sentence_language, sentence_score = classify(sentence)
                            if sentence_score >= confidence:
                                sentence_languages.add(sentence_language)
                    if "en" in sentence_languages and len(sentence_languages) > 1:
                        entry["mixed_sentence"] = True
            if entry["language"] is None and marker:
                entry["language"] = marker
        lines.append(entry)

    languages = {line["language"] for line in lines if line["language"]}
    if whole_score >= confidence and (not languages or whole_language in languages or whole_language == "en"):
        languages.add(whole_language)
    result["detected_languages"] = sorted(languages)
    if any(line.get("mixed_sentence") for line in lines):
        result["sections"] = lines
        return "review", "mixed_sentence_languages", "", result
    if languages == {"en"}:
        result.update(detected_language="en", selected_spans=[{"char_start": 0, "char_end": len(text)}], sections=lines)
        return "keep", "english", text, result
    if "en" not in languages:
        result["sections"] = lines
        if languages:
            result["detected_language"] = whole_language
            return "exclude", "non_english", "", result
        return "review", "uncertain_language", "", result

    foreign_groups = []
    group = []
    for line in lines + [{"language": "en"}]:
        if line["language"] == "en":
            if group:
                foreign_groups.append(group)
            group = []
        elif line["language"]:
            group.append(line)
    for group in foreign_groups:
        passage = "\n".join(text[line["char_start"]:line["char_end"]] for line in group)
        foreign_letters = sum(char.isalpha() and "LATIN" not in unicodedata.name(char, "") for char in passage)
        passage_language, passage_score = classify(passage)
        if passage_language == "en" and passage_score >= confidence:
            result["sections"] = lines
            return "review", "conflicting_language_scores", "", result
        if word_count(passage) < 25 and foreign_letters < 4 and not any(line.get("marker") for line in group):
            result["sections"] = lines
            return "review", "short_language_conflict", "", result

    # Short headings follow the next passage; short sentences follow the previous one.
    for index, line in enumerate(lines):
        if line["language"]:
            continue
        value = text[line["char_start"]:line["char_end"]]
        previous = next((item["language"] for item in reversed(lines[:index]) if item["language"]), None)
        following = next((item["language"] for item in lines[index + 1:] if item["language"]), None)
        if not any(char.isalpha() for char in value):
            line["language"] = previous if previous == following else "separator"
        elif word_count(value) < 8 and sum(char.isalpha() for char in value) < 30:
            line["language"] = (following or previous) if is_heading(value) else (previous or following)
            line["inferred"] = True
        else:
            result["sections"] = lines
            return "review", "uncertain_mixed_section", "", result

    spans = []
    active = None
    for line in lines:
        selected = line["language"] == "en" and not line.get("marker")
        if selected:
            if active is None:
                active = {"char_start": line["char_start"], "char_end": line["char_end"]}
                spans.append(active)
            else:
                active["char_end"] = line["char_end"]
        else:
            active = None
    retrieval_text = "\n\n".join(text[span["char_start"]:span["char_end"]] for span in spans)
    result.update(detected_language="en", sections=lines, selected_spans=spans)
    if not retrieval_text:
        return "review", "english_section_unresolved", "", result
    return "keep", "english_sections_retained", retrieval_text, result


def duplicate_key(review):
    text = unicodedata.normalize("NFC", review["retrieval_text"])
    return str(review["appid"]), re.sub(r"\s+", " ", text).strip().casefold()


def read_reviews(path):
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data["reviews"] if isinstance(data, dict) else data


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def process(reviews, args):
    identifier = LanguageIdentifier.from_modelstring(model, norm_probs=True)
    cleaned_rows, checked = [], []
    for index, review in enumerate(reviews, 1):
        text, actions, urls = clean_formatting(review["review_text"])
        cleaned = {**review, "cleaned_text": text, "cleaning_actions": actions, "extracted_urls": urls}
        cleaned_rows.append(cleaned)
        decision, reason, retrieval_text, language = language_sections(text, identifier, args.confidence)
        if decision == "review":
            language.update(original_reason=reason, language_exclusion_basis="not_confirmed_english")
            decision, reason = "exclude", "non_english"
        checked.append({**cleaned, "retrieval_text": retrieval_text, "quality_check": {"decision": decision, "reason": reason, **language}})
        if index % 1000 == 0:
            print(f"Checked {index}/{len(reviews)} reviews", flush=True)

    groups = defaultdict(list)
    for review in checked:
        key = duplicate_key(review)
        if review["quality_check"]["decision"] == "keep" and key[1]:
            groups[key].append(review)
    for group in groups.values():
        keeper = max(group, key=lambda row: int(row.get("helpful_votes") or 0))
        for review in group:
            if review is not keeper:
                review["quality_check"].update(decision="exclude", reason="duplicate_text", duplicate_of=document_id(keeper))

    kept = [row for row in checked if row["quality_check"]["decision"] == "keep"]
    excluded = [row for row in checked if row["quality_check"]["decision"] == "exclude"]
    candidates = [row for row in checked if row["quality_check"]["decision"] == "review"]
    chunks, split_count = [], 0
    for review in kept:
        text = review["retrieval_text"]
        spans = split_review(text, args.min_words, args.target_words, args.max_words, args.overlap_words)
        validate_spans(text, spans, args.max_words)
        split_count += len(spans) > 1
        for index, (start, end, overlap) in enumerate(spans, 1):
            metadata = {key: value for key, value in review.items() if key not in {"review_text", "cleaned_text", "retrieval_text", "quality_check"}}
            metadata.update({
                "detected_language": review["quality_check"]["detected_language"],
                "language_action": review["quality_check"]["reason"],
                "chunk_index": index, "chunk_count": len(spans),
                "word_count": word_count(text[start:end]),
                "char_start": start, "char_end": end, "offset_text_field": "retrieval_text",
                "overlap_word_count": overlap,
            })
            chunks.append({"id": f"{document_id(review)}:chunk:{index:03d}", "document_id": document_id(review),
                           "text": text[start:end], "source": "steam", "title": f"{review['game_name']} — review {review['review_id']}", "metadata": metadata})

    def distribution(rows):
        positive = sum(bool(row["steam_recommended"]) for row in rows)
        return {"total": len(rows), "recommended": positive, "not_recommended": len(rows) - positive}

    counts = [row["metadata"]["word_count"] for row in chunks]
    report = {
        "input_reviews": len(reviews), "kept_reviews": len(kept), "excluded_reviews": len(excluded), "review_candidates": len(candidates),
        "changed_format_reviews": sum(row["cleaned_text"] != row["review_text"] for row in cleaned_rows),
        "cleaning_action_counts": dict(Counter(action for row in cleaned_rows for action in row["cleaning_actions"])),
        "kept_reason_counts": dict(Counter(row["quality_check"]["reason"] for row in kept)),
        "excluded_reason_counts": dict(Counter(row["quality_check"]["reason"] for row in excluded)),
        "language_exclusion_basis_counts": dict(Counter(
            row["quality_check"].get("language_exclusion_basis", "detected_non_english")
            for row in excluded if row["quality_check"]["reason"] == "non_english"
        )),
        "candidate_reason_counts": dict(Counter(row["quality_check"]["reason"] for row in candidates)),
        "input_distribution": distribution(reviews), "retained_distribution": distribution(kept),
        "words": {"raw": sum(word_count(row["review_text"]) for row in reviews), "format_cleaned": sum(word_count(row["cleaned_text"]) for row in cleaned_rows),
                  "retained_english": sum(word_count(row["retrieval_text"]) for row in kept), "chunks_including_overlap": sum(counts),
                  "retained_case_insensitive_types": len({word.lower() for row in kept for word in WORD_RE.findall(row["retrieval_text"])})},
        "output_chunks": len(chunks), "split_reviews": split_count, "single_chunk_reviews": len(kept) - split_count,
        "overlapping_chunks": sum(row["metadata"]["overlap_word_count"] > 0 for row in chunks),
        "chunk_word_counts": {"minimum": min(counts, default=0), "median": statistics.median(counts) if counts else 0, "maximum": max(counts, default=0)},
        "games": [{"appid": appid, "game_name": next(row["game_name"] for row in reviews if row["appid"] == appid),
                   "collected": distribution([row for row in reviews if row["appid"] == appid]),
                   "retained": distribution([row for row in kept if row["appid"] == appid]),
                   "chunks": sum(row["metadata"]["appid"] == appid for row in chunks)} for appid in dict.fromkeys(row["appid"] for row in reviews)],
        "rules": {
            "language_detector": "langid 1.1.6 with normalized model scores", "language_score_threshold": args.confidence,
            "language_sections": "Keep English text and extract English passages from separated bilingual sections. Archive detected non-English and unresolved review cases under non_english; preserve the original reason for unresolved cases.",
            "short_text": "Retain text with fewer than 30 letters, or Latin-majority text with fewer than 12 words, as language undetermined. Check longer non-Latin text even when word counts are small.",
            "duplicates": "Within each game, compare NFC English retrieval text after case folding and whitespace normalization. Keep the review with most helpful votes; ties keep input order.",
            "formatting": "Retain headings, paragraphs, list structure, selected checkbox values, and explicit struck-through text. Save URLs separately and use <URL> in text.",
            "max_words": args.max_words, "target_words": args.target_words, "preferred_min_words": args.min_words, "overlap_max_words": args.overlap_words,
            "boundaries": "Keep reviews up to max_words whole. Prefer paragraph endings, then sentence endings, near target_words. Use a word boundary for oversized sentences.",
            "overlap": "Reuse at most one complete preceding sentence when it fits both limits.",
            "offsets": "Chunk offsets index retrieval_text; selected language spans index cleaned_text. Both use zero-based Python Unicode character offsets, with an exclusive end.",
            "word_count": "Unicode letter and number groups, with internal apostrophes retained.",
        },
        "validation": {"source_fields_preserved": all(original == {key: row[key] for key in original} for original, row in zip(reviews, checked)),
                       "complete_partition": len(kept) + len(excluded) + len(candidates) == len(reviews), "chunk_coverage": True, "chunk_word_limit": True},
    }
    return {"clean_reviews": cleaned_rows, "filtered_reviews": kept, "excluded_reviews": excluded, "review_candidates": candidates, "chunks": chunks}, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=KNOWLEDGE_BASE_DIR / "all_reviews.json",
                        help="Source reviews JSON or JSONL")
    parser.add_argument("--output", type=Path, default=CHUNKS_PATH.parent,
                        help="Folder for processed reviews, chunks, and the processing report")
    parser.add_argument("--confidence", type=float, default=0.9)
    parser.add_argument("--min-words", type=int, default=100)
    parser.add_argument("--target-words", type=int, default=120)
    parser.add_argument("--max-words", type=int, default=150)
    parser.add_argument("--overlap-words", type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.min_words <= args.target_words <= args.max_words or args.overlap_words < 0:
        parser.error("Use 1 <= min-words <= target-words <= max-words and overlap-words >= 0")
    if not 0 < args.confidence <= 1:
        parser.error("--confidence must be greater than 0 and at most 1")
    rows = read_reviews(args.input)
    outputs, report = process(rows, args)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, records in outputs.items():
        write_jsonl(args.output / f"{name}.jsonl", records)
    (args.output / "processing_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("input_reviews", "kept_reviews", "excluded_reviews", "review_candidates", "output_chunks")}, indent=2))


if __name__ == "__main__":
    main()
