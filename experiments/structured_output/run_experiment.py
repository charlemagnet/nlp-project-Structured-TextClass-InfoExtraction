
import csv
import json
import sys
from pathlib import Path
from time import perf_counter

from pydantic import ValidationError

# Find the main project directory
PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR))

from core.llm_client import analyze_news, load_samples
from core.json_parser import parse_llm_output
from core.schemas import NewsAnalysis

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

CATEGORIES = ["World", "Sports", "Business", "Sci/Tech"]

# Three output generation methods
EXPERIMENTS = [
    ("01_prompt_only", None),
    ("02_json_mode", "json"),
    ("03_json_schema", NewsAnalysis.model_json_schema())
]


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Use the same article for every experiment
    sample = load_samples()[0]

    news_text = sample["text"]
    expected_category = CATEGORIES[sample["label"]]

    results = []

    for name, response_format in EXPERIMENTS:

        print(f"\nRunning: {name}")

        # Measure model response time
        start = perf_counter()

        response = analyze_news(
            news_text,
            instruction_role="system",
            think=False,
            response_format=response_format
        )

        elapsed = perf_counter() - start

        content = response.message.content or ""
        thinking = response.message.thinking or ""

        # Use our existing parser
        parsed = parse_llm_output(content)

        # Validate the parsed result with Pydantic
        pydantic_valid = False

        try:
            NewsAnalysis.model_validate(parsed["data"])
            pydantic_valid = True

        except ValidationError:
            pass

        # Extract predicted category
        data = parsed["data"]

        predicted_category = (
            data.get("category")
            if isinstance(data, dict)
            else None
        )

        # Save raw model outputs
        experiment_dir = OUTPUT_DIR / name
        experiment_dir.mkdir(parents=True, exist_ok=True)

        (experiment_dir / "content.txt").write_text(
            content, encoding="utf-8"
        )

        (experiment_dir / "thinking.txt").write_text(
            thinking, encoding="utf-8"
        )

        # Build evaluation result
        result = {
            "experiment": name,
            "time_seconds": round(elapsed, 2),
            "raw_json_success": parsed["raw_json_success"],
            "recovered_json_success": parsed["recovered_json_success"],
            "schema_valid": parsed["schema_valid"],
            "pydantic_valid": pydantic_valid,
            "raw_schema_success": (
                parsed["raw_json_success"] and pydantic_valid
            ),
            "content_length": len(content),
            "thinking_length": len(thinking),
            "expected_category": expected_category,
            "predicted_category": predicted_category,
            "category_correct": (
                predicted_category == expected_category
                if predicted_category is not None
                else None
            ),
            "done_reason": response.done_reason
        }

        results.append(result)

        with open(experiment_dir / "result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print("Raw JSON:", result["raw_json_success"])
        print("Schema valid:", result["schema_valid"])
        print("Pydantic valid:", pydantic_valid)
        print("Predicted:", predicted_category)
        print("Expected:", expected_category)
        print("Time:", round(elapsed, 2), "seconds")

    # Save all results as CSV
    csv_path = OUTPUT_DIR / "results.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print("\nExperiment completed!")
    print("Results saved to:", csv_path)


if __name__ == "__main__":
    main()
