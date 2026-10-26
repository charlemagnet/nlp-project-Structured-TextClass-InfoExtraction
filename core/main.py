import json
import csv
import re
from pathlib import Path
from time import perf_counter
from ollama import chat

# Settings
MODEL = "qwen3:4b-instruct"
TEMPERATURE = 0
SEED = 42
NUM_PREDICT = 1024
CATEGORIES = ["World", "Sports", "Business", "Sci/Tech"]

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "evaluation_samples.json"
RESULTS = ROOT / "results"

PROMPT = """
You are a news classification and entity extraction system.

Classify the article as World, Sports, Business or Sci/Tech.
Extract explicitly mentioned persons, organizations and locations.

Return ONLY a valid JSON object in this structure:
{
  "category": "World",
  "persons": [],
  "organizations": [],
  "locations": []
}

Do not include explanations, markdown or extra text.
Do not explain your reasoning.
/no_think
"""


# Parse original JSON; clean only if the first attempt fails
def parse_output(text):
    try:
        return json.loads(text), True
    except (json.JSONDecodeError, TypeError):
        pass

    text = text.rsplit("</think>", 1)[-1]

    blocks = re.findall(
        r"```(?:json)?\s*(.*?)```", text, re.S | re.I
    )
    if blocks:
        text = blocks[-1]

    decoder = json.JSONDecoder()

    for i, char in enumerate(text):
        if char == "{":
            try:
                data, _ = decoder.raw_decode(text[i:])
                if isinstance(data, dict):
                    return data, False
            except json.JSONDecodeError:
                continue

    return None, False


# Check the structure without using JSON Schema
def valid_structure(data):
    if not isinstance(data, dict):
        return False

    keys = {"category", "persons", "organizations", "locations"}

    return (
        set(data.keys()) == keys
        and data["category"] in CATEGORIES
        and all(
            isinstance(data[k], list)
            and all(isinstance(x, str) for x in data[k])
            for k in ("persons", "organizations", "locations")
        )
    )


def main():
    samples = json.loads(DATA.read_text(encoding="utf-8"))
    RESULTS.mkdir(exist_ok=True)

    # Automatically create the next run folder
    run = 3
    while (RESULTS / f"run{run}").exists():
        run += 1

    folder = RESULTS / f"run{run}"
    folder.mkdir()

    (folder / "prompt.txt").write_text(PROMPT, encoding="utf-8")

    config = {
        "model": MODEL,
        "temperature": TEMPERATURE,
        "seed": SEED,
        "num_predict": NUM_PREDICT,
        "format": "prompt_only",
        "think": False,
        "sample_count": len(samples)
    }
    (folder / "config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )

    records = []

    for i, sample in enumerate(samples):
        expected = CATEGORIES[sample["label"]]
        start = perf_counter()

        record = {
            "sample_id": i,
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
            "error": None,
            "done_reason": None
        }

        try:
            response = chat(
                model=MODEL,
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": sample["text"]}
                ],
                think=False,
                stream=False,
                options={
                    "temperature": TEMPERATURE,
                    "seed": SEED,
                    "num_predict": NUM_PREDICT
                }
            )

            raw = response.message.content or ""
            data, first_try = parse_output(raw)

            valid = valid_structure(data)
            predicted = data.get("category") if isinstance(data, dict) else None

            record.update({
                "request_ok": True,
                "model_response": raw,
                "parsed_data": data,
                "done_reason": response.done_reason,
                "predicted_category": predicted,
                "raw_json_success": first_try,
                "recovered_json_success": data is not None and not first_try,
                "schema_valid": valid,
                "category_correct": valid and predicted == expected
            })

        except Exception as error:
            record["error"] = str(error)

        record["time_seconds"] = round(perf_counter() - start, 2)
        records.append(record)

        # Save each prediction immediately
        with (folder / "predictions.jsonl").open(
            "a", encoding="utf-8"
        ) as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(
            f"{i + 1}/{len(samples)} | "
            f"JSON: {record['raw_json_success']} | "
            f"Recovered: {record['recovered_json_success']} | "
            f"Valid: {record['schema_valid']} | "
            f"Correct: {record['category_correct']} | "
            f"Time: {record['time_seconds']}s"
        )

    # Calculate evaluation metrics
    total = len(records)
    raw_count = sum(r["raw_json_success"] for r in records)
    recovered = sum(r["recovered_json_success"] for r in records)
    valid_count = sum(r["schema_valid"] for r in records)
    correct = sum(r["category_correct"] for r in records)

    summary = {
        "total_samples": total,
        "raw_json_success_rate": round(raw_count / total * 100, 2),
        "recovered_only_count": recovered,
        "schema_valid_rate": round(valid_count / total * 100, 2),
        "correct_category_count": correct,
        "category_accuracy": round(correct / total * 100, 2)
    }

    (folder / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    columns = [
        "sample_id", "expected_category", "predicted_category",
        "request_ok", "raw_json_success", "recovered_json_success",
        "schema_valid", "category_correct",
        "time_seconds", "done_reason", "error"
    ]

    with (folder / "results.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(
            {k: r[k] for k in columns} for r in records
        )

    print("\nFINAL RESULTS")
    print(json.dumps(summary, indent=2))
    print("Saved to:", folder)


if __name__ == "__main__":
    main()
