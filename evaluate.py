import argparse
import csv
import json 
from pathlib import Path
from time import perf_counter

from pydantic import ValidationError

from llm_client import analyze_news, load_samples
from json_parser import parse_llm_output
from schemas import NewsAnalysis

# Project settings
RESULTS_DIR = Path(__file__).resolve().parent / "results"

PREDICTIONS_FILE = RESULTS_DIR / "predictions.jsonl"
CSV_FILE = RESULTS_DIR / "results.csv"
SUMMARY_FILE = RESULTS_DIR / "summary.json"

CATEGORIES = ["World", "Sports", "Business", "Sci/Tech"]

# Load previous evaluated samples
def load_previous_results():

    if not PREDICTIONS_FILE.exists():
        return {}

    previous = {}

    with open(PREDICTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                previous[record["sample_id"]] = record

    return previous

# Evaluate a single news article
def evaluate_one(sample_id, sample):

    expected_category = CATEGORIES[sample["label"]]

    record = {
        "sample_id": sample_id,
        "news_text": sample["text"],
        "expected_category": expected_category,
        "predicted_category": None,
        "request_ok": False,
        "raw_json_success": False,
        "schema_valid": False,
        "category_correct": False,
        "model_response": None,
        "parsed_data": None,
        "parse_error": None,
        "error": None,
        "done_reason": None,
        "recovered_json_success": False,
        "time_seconds": None
    }

    start = perf_counter()

    try:
        # Step 1: Call the local LLM
        response = analyze_news(
            sample["text"],
            instruction_role="system",
            think=False,
            response_format=NewsAnalysis.model_json_schema()
        )

        record["request_ok"] = True
        record["done_reason"] = response.done_reason

        content = response.message.content or ""
        record["model_response"] = content

        # Step 2: Parse the JSON
        parsed = parse_llm_output(content)

        record["raw_json_success"] = parsed["raw_json_success"]
        record["recovered_json_success"] = parsed["recovered_json_success"]
        record["parse_error"] = parsed["first_error"]

        data = parsed["data"]
        record["parsed_data"] = data

        # Step 3: Validate data with Pydantic
        if isinstance(data, dict):

            record["predicted_category"] = data.get("category")

            try:
                NewsAnalysis.model_validate(data, strict=True)
                record["schema_valid"] = True

            except ValidationError as error:
                record["error"] = str(error)

        # Step 4: Compare prediction with actual label
        record["category_correct"] = (
            record["schema_valid"]
            and record["predicted_category"] == expected_category
        )

    except Exception as error:
        # A single faile sample must not stop the experiment
        record["error"] = f"{type(error).__name__}: {error}"

    finally:
        record["time_seconds"] = round(
            perf_counter() - start, 2
        )

    return record

# Calculate metrics and save reports
def save_reports(records):

    records = sorted(
        records,
        key=lambda item: item["sample_id"]
    )

    total = len(records)

    raw_count = sum(r["raw_json_success"] for r in records)
    recovered_count = sum(r["recovered_json_success"] for r in records)
    schema_count = sum(r["schema_valid"] for r in records)
    correct_count = sum(r["category_correct"] for r in records)
    response_count = sum(r["request_ok"] for r in records)

    summary = {
        "total_samples": total,
        "responses_received": response_count,
        "request_failures": total - response_count,
        "raw_json_success_count": raw_count,
        "raw_json_success_rate": round(100 * raw_count / total, 2),
        "recovered_only_count": recovered_count,
        "schema_valid_count": schema_count,
        "schema_valid_rate": round(100 * schema_count / total, 2),
        "correct_category_count": correct_count,
        "category_accuracy": round(100 * correct_count / total, 2)
    }

    # Save summary as JSON
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Save compact results as CSV
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

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for record in records:
            writer.writerow({
                column: record[column]
                for column in columns
            })

    return summary

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    # Load our 120 news articles
    dataset = load_samples()

    if not 1 <= args.limit <= len(dataset):
        parser.error(
            f"--limit must be between 1 and {len(dataset)}"
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load completed evaluations
    previous = load_previous_results()

    # Process articles one by one
    for index in range(args.limit):

        if index in previous:
            print(f"Sample {index + 1}: already evaluated, skipping")
            continue

        sample = dataset[index]

        print(f"\nEvaluating {index + 1}/{args.limit}")

        result = evaluate_one(index, sample)

        # Save every result immediately
        with open(PREDICTIONS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

        previous[index] = result

        print("Expected:", result["expected_category"])
        print("Predicted:", result["predicted_category"])
        print("Raw JSON:", result["raw_json_success"])
        print("Schema valid:", result["schema_valid"])
        print("Category correct:", result["category_correct"])

        if result["error"]:
            print("Error:", result["error"][:200])

    # Generate reports for the requested sample range
    selected_results = [
        previous[i]
        for i in range(args.limit)
    ]

    summary = save_reports(selected_results)

    print("\n=== EVALUATION SUMMARY ===")

    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\nResults saved to:", RESULTS_DIR)


if __name__ == "__main__":
    main()