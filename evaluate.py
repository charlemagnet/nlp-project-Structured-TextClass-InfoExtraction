import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from time import perf_counter

from pydantic import ValidationError

from llm_client import (
    analyze_news,
    load_samples,
    MODEL,
    OPTIONS,
    DATA_FILE
)

from prompts import TASK_INSTRUCTIONS, PROMPT_VERSION
from schemas import NewsAnalysis
from json_parser import parse_llm_output
from report_results import generate_report


ROOT = Path(__file__).resolve().parent
CATEGORIES = ["World", "Sports", "Business", "Sci/Tech"]


def evaluate_one(sample_id, sample):

    expected = CATEGORIES[sample["label"]]

    row = {
        "sample_id": sample_id,
        "news_text": sample["text"],
        "expected_category": expected,
        "predicted_category": None,
        "request_ok": False,
        "raw_json_success": False,
        "recovered_json_success": False,
        "schema_valid": False,
        "category_correct": False,
        "model_response": None,
        "parsed_data": None,
        "parse_error": None,
        "error": None,
        "done_reason": None,
        "time_seconds": None
    }

    start = perf_counter()

    try:
        response = analyze_news(
            sample["text"],
            instruction_role="system",
            think=False,
            response_format=NewsAnalysis.model_json_schema()
        )

        row["request_ok"] = True
        row["done_reason"] = response.done_reason

        content = response.message.content or ""
        row["model_response"] = content

        parsed = parse_llm_output(content)

        row["raw_json_success"] = parsed["raw_json_success"]
        row["recovered_json_success"] = parsed["recovered_json_success"]
        row["parse_error"] = parsed["first_error"]
        row["parsed_data"] = parsed["data"]

        if isinstance(parsed["data"], dict):

            row["predicted_category"] = (
                parsed["data"].get("category")
            )

            try:
                NewsAnalysis.model_validate(
                    parsed["data"],
                    strict=True
                )
                row["schema_valid"] = True

            except ValidationError as error:
                row["error"] = str(error)

        row["category_correct"] = (
            row["schema_valid"]
            and row["predicted_category"] == expected
        )

    except Exception as error:
        row["error"] = f"{type(error).__name__}: {error}"

    finally:
        row["time_seconds"] = round(
            perf_counter() - start, 2
        )

    return row


def prepare_run(folder, dataset):

    # Save all settings needed to identify this experiment
    config = {
        "model": MODEL,
        "options": OPTIONS,
        "instruction_role": "system",
        "think": False,
        "format": "json_schema",
        "prompt_version": PROMPT_VERSION,
        "dataset_sha256": hashlib.sha256(
            DATA_FILE.read_bytes()
        ).hexdigest(),
        "dataset_size": len(dataset)
    }

    config_path = folder / "config.json"
    prompt_path = folder / "prompt.txt"

    # Resume only if the old settings match
    if config_path.exists() and prompt_path.exists():

        old_config = json.loads(
            config_path.read_text(encoding="utf-8")
        )

        old_prompt = prompt_path.read_text(
            encoding="utf-8"
        )

        if old_config != config or old_prompt != TASK_INSTRUCTIONS:
            raise RuntimeError(
                "Run settings changed. Use a NEW run folder."
            )

    elif any(folder.iterdir()):
        raise RuntimeError(
            "Nonempty run folder without a complete snapshot. "
            "Refusing to mix runs."
        )

    else:
        config_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        prompt_path.write_text(
            TASK_INSTRUCTIONS,
            encoding="utf-8"
        )


def read_previous(file):

    if not file.exists():
        return {}

    previous = {}

    with file.open("r", encoding="utf-8") as f:
        for line in f:

            if line.strip():
                row = json.loads(line)
                previous[row["sample_id"]] = row

    return previous


def write_summary(run_dir, rows):

    n = len(rows)

    def count(key):
        return sum(bool(r[key]) for r in rows)

    summary = {
        "total_samples": n,
        "responses_received": count("request_ok"),
        "request_failures": n - count("request_ok"),
        "raw_json_success_count": count("raw_json_success"),
        "raw_json_success_rate": round(
            100 * count("raw_json_success") / n, 2
        ),
        "recovered_only_count": count("recovered_json_success"),
        "schema_valid_count": count("schema_valid"),
        "schema_valid_rate": round(
            100 * count("schema_valid") / n, 2
        ),
        "correct_category_count": count("category_correct"),
        "category_accuracy": round(
            100 * count("category_correct") / n, 2
        )
    }

    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8"
    )

    columns = [
        "sample_id",
        "expected_category",
        "predicted_category",
        "request_ok",
        "raw_json_success",
        "recovered_json_success",
        "schema_valid",
        "category_correct",
        "time_seconds",
        "done_reason",
        "error"
    ]

    with (run_dir / "results.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:

        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for row in rows:
            writer.writerow({
                column: row.get(column)
                for column in columns
            })

    return summary


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--run", required=True)
    parser.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()

    # Valid names: run1, run2, run3...
    if not re.fullmatch(r"run[1-9][0-9]*", args.run):
        parser.error("Run name must be run1, run2, run3, ...")

    dataset = load_samples()

    if not 1 <= args.limit <= len(dataset):
        parser.error(
            f"Limit must be 1..{len(dataset)}"
        )

    # Create a separate folder for this run
    folder = ROOT / "results" / args.run
    folder.mkdir(parents=True, exist_ok=True)

    prepare_run(folder, dataset)

    prediction_path = folder / "predictions.jsonl"

    previous = read_previous(prediction_path)

    for i in range(args.limit):

        if i in previous:
            print(
                f"Sample {i + 1}: already evaluated, skipping"
            )
            continue

        print(f"Evaluating {i + 1}/{args.limit}")

        result = evaluate_one(i, dataset[i])

        # Save after each model response
        with prediction_path.open(
            "a", encoding="utf-8"
        ) as f:
            f.write(
                json.dumps(result, ensure_ascii=False) + "\n"
            )

        previous[i] = result

        print(
            "Expected:", result["expected_category"],
            "Predicted:", result["predicted_category"],
            "Correct:", result["category_correct"]
        )

    rows = [previous[i] for i in range(args.limit)]

    summary = write_summary(folder, rows)

    print("\nSummary:", summary)

    # Automatically compare with the previous run
    previous_name = f"run{int(args.run[3:]) - 1}"

    baseline = (
        previous_name
        if (
            ROOT / "results" / previous_name / "results.csv"
        ).exists()
        else None
    )

    generate_report(args.run, compare=baseline)


if __name__ == "__main__":
    main()
