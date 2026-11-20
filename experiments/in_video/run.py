"""120 veri seti haberi ve bes yeni haberi calistir; her deneyi yeni klasore kaydet."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ollama import chat
from core.main import (
    CATEGORIES, DATA, MODEL, NUM_CTX, NUM_PREDICT, PROMPT, SEED,
    parse_output, valid_structure,
)
from core.schemas import NewsAnalysis

OUTPUT = Path(__file__).resolve().parent

# Video icin uretilmis, gercek haber olmayan bes yeni ornek.
# expected_category yalnizca yorumlamak icindir; modele gonderilmez.
SAMPLES = [
    {
        "text": "The governments of Canada and Norway signed a climate cooperation agreement in Oslo.",
        "expected_category": "World",
    },
    {
        "text": "The Ankara Falcons defeated the Izmir Tigers 3-1 in a football match in Istanbul.",
        "expected_category": "Sports",
    },
    {
        "text": "Atlas Foods reported a 12 percent rise in quarterly revenue after opening stores in Berlin.",
        "expected_category": "Business",
    },
    {
        "text": "Researchers at Delft University of Technology developed a battery that charges in five minutes.",
        "expected_category": "Sci/Tech",
    },
    {
        # hard example
        "text": "Atlas Football Club announced that it will buy a cybersecurity company for five billion dollars, causing its shares to rise 20 percent.",
        "expected_category": "Business",
        "expected_difficulty": "A generic company description may be extracted as a named organization; the category may also be ambiguous.",
    },
]


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def new_run_folder():
    """Var olan run klasorlerine dokunmadan ilk bos numarayi ayir."""
    number = 1
    while True:
        folder = OUTPUT / f"run{number}"
        try:
            folder.mkdir(parents=True)
            return folder
        except FileExistsError:
            number += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", "-mode", choices=["prompt-only", "schema"],
                        default="prompt-only", help="Cikti ayari")
    parser.add_argument("--temperature", "-temperature", type=float, default=0.0,
                        help="Ornegin 0 veya 1")
    args = parser.parse_args()
    if not 0 <= args.temperature <= 2:
        parser.error("temperature 0 ile 2 arasinda olmali")

    dataset = json.loads(DATA.read_text(encoding="utf-8"))
    def normalized(text):
        return " ".join(text.split()).casefold()
    known_texts = {normalized(sample["text"]) for sample in dataset}
    if len(SAMPLES) < 5 or any(normalized(sample["text"]) in known_texts for sample in SAMPLES):
        raise SystemExit("En az 5 yeni metin gerekli; bir ornek degerlendirme veri setiyle ayni.")

    # Once 120 degerlendirme haberi, ardindan videodaki bes yeni haber.
    samples = [
        {"source": "dataset", "source_sample_id": i, "text": sample["text"],
         "expected_category": CATEGORIES[sample["label"]]}
        for i, sample in enumerate(dataset)
    ]
    samples += [
        {**sample, "source": "new", "source_sample_id": i}
        for i, sample in enumerate(SAMPLES, 1)
    ]

    folder = new_run_folder()
    config = {
        "model": MODEL, "mode": args.mode, "temperature": args.temperature,
        "seed": SEED, "num_predict": NUM_PREDICT, "num_ctx": NUM_CTX,
        "think": False, "stream": False, "sample_count": len(samples),
        "dataset_sample_count": len(dataset), "new_sample_count": len(SAMPLES),
        "dataset_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
        "prompt_sha256": hashlib.sha256(PROMPT.encode("utf-8")).hexdigest(),
        "description": "Dataset labels and informal expectations for new synthetic samples are not sent to the model.",
    }
    if args.mode == "schema":
        config["json_schema"] = NewsAnalysis.model_json_schema()
    save_json(folder / "config.json", config)
    save_json(folder / "samples.json", samples)
    (folder / "prompt.txt").write_text(PROMPT, encoding="utf-8")

    print(f"Results: {folder}", flush=True)
    print(f"Model: {MODEL} | Mode: {args.mode} | Temperature: {args.temperature}", flush=True)
    print(f"Samples: {len(dataset)} dataset articles + {len(SAMPLES)} new synthetic examples", flush=True)
    records = []
    failed = False
    for i, sample in enumerate(samples, 1):
        print(f"\n--- Sample {i}/{len(samples)} | {sample['source']} {sample['source_sample_id']} ---", flush=True)
        print("Text:", sample["text"], flush=True)
        expected_label = "Dataset label" if sample["source"] == "dataset" else "Expected category (informal)"
        print(f"{expected_label}:", sample["expected_category"], flush=True)
        if "expected_difficulty" in sample:
            print("Expected difficulty:", sample["expected_difficulty"], flush=True)

        record = {
            "sample_id": i, "source": sample["source"],
            "source_sample_id": sample["source_sample_id"], "text": sample["text"],
            "expected_category": sample["expected_category"], "request_ok": False,
            "model_response": None, "parsed_data": None, "predicted_category": None,
            "raw_json_success": False, "recovered_only": False,
            "schema_valid": False, "category_correct": None, "done_reason": None, "error": None,
        }
        request = {
            "model": MODEL,
            "messages": [{"role": "system", "content": PROMPT},
                         {"role": "user", "content": sample["text"]}],
            "think": False, "stream": False,
            "options": {"temperature": args.temperature, "seed": SEED,
                        "num_predict": NUM_PREDICT, "num_ctx": NUM_CTX},
        }
        if args.mode == "schema":
            request["format"] = NewsAnalysis.model_json_schema()

        start = perf_counter()
        try:
            response = chat(**request)
            raw = response.message.content or ""
            data, first_try = parse_output(raw)
            record.update(
                request_ok=True, model_response=raw, parsed_data=data,
                predicted_category=data.get("category") if isinstance(data, dict) else None,
                raw_json_success=first_try, recovered_only=data is not None and not first_try,
                schema_valid=valid_structure(data), done_reason=response.done_reason,
            )
            if sample["source"] == "dataset":
                record["category_correct"] = (
                    record["schema_valid"] and record["predicted_category"] == sample["expected_category"]
                )
            print("Raw response:", raw, flush=True)
            print("Raw JSON:", first_try, "| Valid structure:", record["schema_valid"], flush=True)
            print("Parsed output:", json.dumps(data, ensure_ascii=False), flush=True)
        except Exception as error:
            failed = True
            record["error"] = f"{type(error).__name__}: {error}"
            print("Ollama error:", record["error"], flush=True)
        record["time_seconds"] = round(perf_counter() - start, 2)
        records.append(record)
        with (folder / "predictions.jsonl").open("a", encoding="utf-8") as output:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
        if failed:
            break

    total = len(records)
    raw_count = sum(row["raw_json_success"] for row in records)
    recovered = sum(row["recovered_only"] for row in records)
    valid_count = sum(row["schema_valid"] for row in records)
    dataset_rows = [row for row in records if row["source"] == "dataset"]
    new_rows = [row for row in records if row["source"] == "new"]
    dataset_correct = sum(row["category_correct"] is True for row in dataset_rows)
    summary = {
        "requested_samples": len(samples), "processed_samples": total,
        "completed": not failed and total == len(samples),
        "request_failures": sum(not row["request_ok"] for row in records),
        "raw_json_success": f"{raw_count}/{total}",
        "after_cleaning_json_success": f"{raw_count + recovered}/{total}",
        "schema_valid": f"{valid_count}/{total}",
        "dataset_results": {
            "requested_samples": len(dataset), "processed_samples": len(dataset_rows),
            "correct_categories": dataset_correct,
            "classification_accuracy": round(100 * dataset_correct / len(dataset_rows), 2) if dataset_rows else None,
        },
        "new_samples": {
            "requested_samples": len(SAMPLES), "processed_samples": len(new_rows),
            "note": "Informal expected categories; inspect outputs individually.",
        },
        "note": "Classification accuracy uses dataset examples only; no entity F1 is computed in this run.",
    }
    save_json(folder / "summary.json", summary)
    print("\nSummary:", json.dumps(summary, ensure_ascii=False), flush=True)
    print("Saved to:", folder, flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
