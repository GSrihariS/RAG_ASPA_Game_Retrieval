"""Calculate sentiment agreement from two compact sets of aspect labels."""

import argparse
from collections import Counter
import json
from pathlib import Path

from paths import EVALUATION_DATASET_DIR


def agreement(left, right):
    count = len(left)
    matches = sum(a == b for a, b in zip(left, right))
    if not count:
        return {"compared_labels": 0, "matching_labels": 0,
                "agreement_percent": None, "cohen_kappa": None}
    observed = matches / count
    counts_a, counts_b = Counter(left), Counter(right)
    expected = sum(counts_a[label] * counts_b[label] for label in counts_a) / count ** 2
    kappa = (observed - expected) / (1 - expected) if expected < 1 else None
    return {"compared_labels": count, "matching_labels": matches,
            "agreement_percent": round(100 * observed, 4),
            "cohen_kappa": round(kappa, 6) if kappa is not None else None}


def read_pairs(data):
    aspects = data["aspect_order"]
    codes = data["sentiment_codes"]
    same = data.get("same_as_annotator_1", "=")
    if not aspects or len(set(aspects)) != len(aspects):
        raise ValueError("aspect_order must contain distinct aspect names")
    if not codes or any(not isinstance(code, str) or len(code) != 1 for code in codes):
        raise ValueError("Each sentiment code must be one character")
    if same in codes:
        raise ValueError("The reference marker must differ from sentiment codes")
    records = data["records"]
    if not records:
        raise ValueError("No annotation records found")
    pairs, seen = [], set()
    for record in records:
        sample_id = record["sample_id"]
        if sample_id in seen:
            raise ValueError(f"Duplicate sample ID: {sample_id}")
        seen.add(sample_id)
        left, right = record["annotator_1"], record["annotator_2"]
        if right == same:
            right = left
        for value in (left, right):
            if not isinstance(value, str) or len(value) != len(aspects) or any(code not in codes for code in value):
                raise ValueError(f"{sample_id}: expected {len(aspects)} valid sentiment codes")
        pairs.append((left, right))
    return aspects, pairs


def calculate(data):
    if not isinstance(data, dict):
        raise ValueError("Input must be a JSON object")
    data = data.get("iaa_annotations", data)
    if not isinstance(data, dict):
        raise ValueError("iaa_annotations must be a JSON object")
    aspects, pairs = read_pairs(data)
    left = [code for a, _ in pairs for code in a]
    right = [code for _, b in pairs for code in b]
    absent = [code for code, label in data["sentiment_codes"].items() if label == "Not mentioned"]
    if len(absent) != 1:
        raise ValueError("sentiment_codes must define exactly one Not mentioned code")
    mentioned = [(a, b) for a, b in zip(left, right) if a != absent[0] or b != absent[0]]
    matches = sum(a == b for a, b in pairs)
    stage = data.get("annotation_stage", "unspecified")
    return {
        "dataset_id": data.get("dataset_id"),
        "annotation_stage": stage,
        "recording_method": data.get("recording_method", "unspecified"),
        "baseline_source": data.get("baseline_source"),
        "independent_pre_review_annotations": data.get("independent_pre_review_annotations"),
        "measurement": "post_review_consensus_agreement" if stage == "post_review_consensus" else "label_agreement",
        "records": len(pairs),
        "aspects_per_record": len(aspects),
        "record_exact_match": {"matching_records": matches,
                               "agreement_percent": round(100 * matches / len(pairs), 4)},
        "sentiment": agreement(left, right),
        "mentioned_sentiment": agreement([a for a, _ in mentioned], [b for _, b in mentioned]),
        "per_aspect": {aspect: agreement([a[i] for a, _ in pairs], [b[i] for _, b in pairs])
                       for i, aspect in enumerate(aspects)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=EVALUATION_DATASET_DIR / "steam_annotations_iaa.json")
    parser.add_argument("--output", type=Path, default=EVALUATION_DATASET_DIR / "iaa_report.json")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        report = calculate(data)
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Stage: {report['annotation_stage']}")
    print(f"Records: {report['records']}")
    print(f"Passage exact agreement: {report['record_exact_match']['agreement_percent']:.2f}%")
    print(f"Aspect-label agreement: {report['sentiment']['agreement_percent']:.3f}%")
    print(f"Cohen's kappa: {report['sentiment']['cohen_kappa']}")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
