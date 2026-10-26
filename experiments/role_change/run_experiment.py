
import csv
import json
import sys
from pathlib import Path
from time import perf_counter

# Import functions from the main project
PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR))

from core.llm_client import (
    MODEL,
    OPTIONS,
    load_samples,
    build_messages,
    analyze_news
)

# Experiment settings
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

CONDITIONS = [
    ("01_user_think_false", "user", False),
    ("02_user_think_true", "user", True),
    ("03_system_think_false", "system", False),
    ("04_system_think_true", "system", True)
]

CATEGORIES = ["World", "Sports", "Business", "Sci/Tech"]


# Save Python objects as JSON
def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# Try to parse a JSON object
def parse_json_object(text):
    try:
        parsed = json.loads(text)

        if isinstance(parsed, dict):
            return parsed

    except (json.JSONDecodeError, TypeError):
        pass

    return None


# Check required JSON fields and types
def validate_schema(data):
    if not isinstance(data, dict):
        return False

    required = {
        "category",
        "persons",
        "organizations",
        "locations"
    }

    return (
        set(data.keys()) == required
        and data["category"] in CATEGORIES
        and all(
            isinstance(data[key], list)
            and all(isinstance(item, str) for item in data[key])
            for key in ("persons", "organizations", "locations")
        )
    )


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Use the same article in every experiment
    sample = load_samples()[0]
    news_text = sample["text"]
    expected_category = CATEGORIES[sample["label"]]

    results = []

    for name, role, think in CONDITIONS:

        print(f"\nRunning: {name}")

        experiment_dir = OUTPUT_DIR / name
        experiment_dir.mkdir(parents=True, exist_ok=True)

        # Save the exact request configuration
        request = {
            "model": MODEL,
            "messages": build_messages(news_text, role),
            "think": think,
            "options": OPTIONS
        }

        save_json(experiment_dir / "request.json", request)

        # Call the model and measure elapsed time
        start = perf_counter()

        response = analyze_news(
            news_text,
            instruction_role=role,
            think=think
        )

        elapsed = perf_counter() - start

        content = response.message.content or ""
        thinking = response.message.thinking or ""

        # Save original outputs without modifications
        (experiment_dir / "content.txt").write_text(
            content, encoding="utf-8"
        )

        (experiment_dir / "thinking.txt").write_text(
            thinking, encoding="utf-8"
        )

        # First-try JSON parsing
        raw_data = parse_json_object(content)
        raw_success = raw_data is not None

        # Diagnostic recovery after </think>
        recovered_data = None

        if "</think>" in content:
            cleaned_content = content.rsplit("</think>", 1)[-1].strip()
            recovered_data = parse_json_object(cleaned_content)

        recovery_success = recovered_data is not None

        # Select data for analysis, without changing raw metrics
        parsed_data = raw_data if raw_success else recovered_data

        predicted_category = (
            parsed_data.get("category")
            if parsed_data is not None
            else None
        )

        # Store experiment measurements
        result = {
            "experiment": name,
            "instruction_role": role,
            "think": think,
            "time_seconds": round(elapsed, 2),
            "content_length": len(content),
            "thinking_length": len(thinking),
            "inline_think_marker": "</think>" in content,
            "raw_json_success": raw_success,
            "after_think_json_success": recovery_success,
            "schema_valid": validate_schema(parsed_data),
            "expected_category": expected_category,
            "predicted_category": predicted_category,
            "category_correct": (
                predicted_category == expected_category
                if predicted_category is not None
                else None
            ),
            "done_reason": getattr(response, "done_reason", None)
        }

        results.append(result)
        save_json(experiment_dir / "result.json", result)

        print("Raw JSON:", raw_success)
        print("After </think> recovery:", recovery_success)
        print("Thinking field length:", len(thinking))
        print("Content length:", len(content))
        print("Time:", round(elapsed, 2), "seconds")

    # Save CSV comparison
    csv_path = OUTPUT_DIR / "results.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # Build Markdown comparison report
    lines = [
        "# Role and Thinking Experiment",
        "",
        f"Model: {MODEL}",
        f"Expected category: {expected_category}",
        "",
        "| Experiment | Time (s) | Content chars | Thinking chars | Raw JSON | Recovered JSON |",
        "|---|---:|---:|---:|---|---|"
    ]

    for result in results:
        lines.append(
            f"| {result['experiment']} "
            f"| {result['time_seconds']} "
            f"| {result['content_length']} "
            f"| {result['thinking_length']} "
            f"| {result['raw_json_success']} "
            f"| {result['after_think_json_success']} |"
        )

    lines.extend([
        "",
        "## Interpretation notes",
        "",
        "- All experiments use the same article and task instructions.",
        "- Only instruction role and thinking mode change.",
        "- Raw JSON success is measured before any cleaning.",
        "- Recovered JSON is measured separately after removing the inline thinking prefix.",
        "- One article is not enough to establish general performance."
    ])

    report_path = OUTPUT_DIR / "comparison.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print("\nExperiment completed.")
    print("CSV:", csv_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
