"""Ayni haberleri prompt-only ve JSON Schema ile degerlendirir."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ollama import chat
from core.main import (CATEGORIES, DATA, MODEL, NUM_CTX, NUM_PREDICT, PROMPT,
                       SEED, TEMPERATURE, parse_output, valid_structure)
from core.schemas import NewsAnalysis

FOLDER = Path(__file__).resolve().parent
GOLD = ROOT / "data" / "gold_labels.json"
KEYS = ("persons", "organizations", "locations")


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_dataset():
    return json.loads(DATA.read_text(encoding="utf-8"))


def prepare_gold(samples):
    if GOLD.exists():
        raise SystemExit(f"Etiket dosyasi zaten var, uzerine yazilmadi: {GOLD}")
    rows = [{"sample_id": i, "text": sample["text"],
             "persons": None, "organizations": None, "locations": None}
            for i, sample in enumerate(samples)]
    write_json(GOLD, rows)
    print(f"Etiketleme dosyasi olusturuldu: {GOLD}")
    print("Her null degerini elle doldurun; varlik yoksa [] yazin.")


def read_gold(samples):
    if not GOLD.exists():
        return {}, "Gold dosyasi yok: once prepare-gold calistirin."
    rows = json.loads(GOLD.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or len(rows) != len(samples):
        raise ValueError("Gold dosyasindaki ornek sayisi veri setiyle uyusmuyor.")
    gold = {}
    for row in rows:
        i = row.get("sample_id")
        if not isinstance(i, int) or isinstance(i, bool) or not 0 <= i < len(samples) or i in gold:
            raise ValueError("Gold dosyasinda gecersiz veya tekrar eden sample_id var.")
        if row.get("text") != samples[i]["text"]:
            raise ValueError(f"Gold metni veri setiyle uyusmuyor: sample_id={i}")
        for key in KEYS:
            values = row.get(key)
            if values is not None and (not isinstance(values, list) or
                    any(not isinstance(value, str) or not value.strip() for value in values)):
                raise ValueError(f"Gecersiz gold etiketi: sample_id={i}, alan={key}")
        gold[i] = row
    return gold, None


def entity_scores(rows, gold):
    complete = [r for r in rows if r["sample_id"] in gold and
                all(gold[r["sample_id"]][k] is not None for k in KEYS)]
    if len(complete) != len(rows) or not rows:
        return {"status": "incomplete_gold", "annotated_samples": len(complete),
                "evaluated_samples": len(rows), "precision": None, "recall": None, "f1": None}
    counts = {key: {"tp": 0, "fp": 0, "fn": 0} for key in KEYS}
    for row in rows:
        prediction = row["parsed_data"] if row["schema_valid"] else {}
        for key in KEYS:
            expected = set(gold[row["sample_id"]][key])
            predicted = set(prediction.get(key, []))
            counts[key]["tp"] += len(expected & predicted)
            counts[key]["fp"] += len(predicted - expected)
            counts[key]["fn"] += len(expected - predicted)

    def metrics(tp, fp, fn):
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 4),
                "recall": round(recall, 4), "f1": round(f1, 4)}

    totals = {name: sum(counts[key][name] for key in KEYS) for name in ("tp", "fp", "fn")}
    return {"status": "complete", "matching": "exact, case-sensitive; unique strings per sample and type",
            **metrics(**totals), "by_type": {key: metrics(**counts[key]) for key in KEYS}}


def summarize(rows, gold):
    n = len(rows)
    def rate(count):
        return round(100 * count / n, 2) if n else 0.0
    raw = sum(r["raw_json_success"] for r in rows)
    recovered = sum(r["recovered_only"] for r in rows)
    return {"total_samples": n, "request_failures": sum(not r["request_ok"] for r in rows),
            "raw_json_success_count": raw, "raw_json_success_rate": rate(raw),
            "recovered_only_count": recovered,
            "after_cleaning_success_count": raw + recovered,
            "after_cleaning_success_rate": rate(raw + recovered),
            "schema_valid_rate": rate(sum(r["schema_valid"] for r in rows)),
            "classification_accuracy": rate(sum(r["category_correct"] for r in rows)),
            "gold_label_file": str(GOLD.relative_to(ROOT)),
            "gold_label_sha256": hashlib.sha256(GOLD.read_bytes()).hexdigest() if GOLD.exists() else None,
            "entity_extraction_micro": entity_scores(rows, gold)}


def ollama_version():
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=5)
        return (result.stdout + result.stderr).strip()
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def config_for(mode):
    return {"model": MODEL, "temperature": TEMPERATURE, "seed": SEED,
            "num_predict": NUM_PREDICT, "num_ctx": NUM_CTX, "think": False,
            "format": mode, "ollama_version": ollama_version(),
            "dataset_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
            "prompt_sha256": hashlib.sha256(PROMPT.encode("utf-8")).hexdigest(),
            "schema": NewsAnalysis.model_json_schema() if mode == "schema" else None}


def load_records(path):
    if not path.exists():
        return {}
    records = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row["sample_id"] in records:
                raise ValueError("Tahmin dosyasinda tekrar eden sample_id var.")
            records[row["sample_id"]] = row
    return records


def run_mode(mode, samples, limit, gold):
    folder = FOLDER / mode
    folder.mkdir(exist_ok=True)
    config_path, prompt_path = folder / "config.json", folder / "prompt.txt"
    config = config_for(mode)
    if config_path.exists() and prompt_path.exists():
        if json.loads(config_path.read_text(encoding="utf-8")) != config or prompt_path.read_text(encoding="utf-8") != PROMPT:
            raise SystemExit(f"{folder}: ayarlar degismis; eski deneye dokunulmadi.")
    elif any(folder.iterdir()):
        raise SystemExit(f"{folder}: deney kaydi eksik; eski dosyalara dokunulmadi.")
    else:
        write_json(config_path, config)
        prompt_path.write_text(PROMPT, encoding="utf-8")
    path = folder / "predictions.jsonl"
    records = load_records(path)
    for i, sample in enumerate(samples[:limit]):
        if i in records:
            continue
        row = {"sample_id": i, "expected_category": CATEGORIES[sample["label"]],
               "request_ok": False, "raw_json_success": False, "recovered_only": False,
               "schema_valid": False, "category_correct": False, "model_response": None,
               "parsed_data": None, "error": None, "done_reason": None}
        start = perf_counter()
        try:
            request = {"model": MODEL, "messages": [{"role": "system", "content": PROMPT},
                       {"role": "user", "content": sample["text"]}], "think": False,
                       "stream": False, "options": {"temperature": TEMPERATURE, "seed": SEED,
                       "num_predict": NUM_PREDICT, "num_ctx": NUM_CTX}}
            if mode == "schema":
                request["format"] = NewsAnalysis.model_json_schema()
            response = chat(**request)
            raw = response.message.content or ""
            parsed, first = parse_output(raw)
            valid = valid_structure(parsed)
            row.update(request_ok=True, model_response=raw, parsed_data=parsed,
                       done_reason=response.done_reason, raw_json_success=first,
                       recovered_only=parsed is not None and not first, schema_valid=valid,
                       category_correct=valid and parsed["category"] == row["expected_category"])
        except Exception as error:
            row["error"] = f"{type(error).__name__}: {error}"
        row["time_seconds"] = round(perf_counter() - start, 2)
        if not row["request_ok"]:
            print(f"Istek basarisiz: {row['error']} - deney durduruldu.", flush=True)
            write_json(folder / "summary.json", summarize([records[j] for j in sorted(records)], gold))
            raise SystemExit("Basarisiz istek kaydedilmedi; sorun cozulunce deney devam edebilir.")
        with path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
        records[i] = row
        print(f"{mode} {i + 1}/{limit}: JSON={row['raw_json_success']} "
              f"yapi={row['schema_valid']} dogru={row['category_correct']}", flush=True)
    rows = [records[i] for i in sorted(records)]
    write_json(folder / "summary.json", summarize(rows, gold))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare-gold", "run", "report"])
    parser.add_argument("--mode", choices=["both", "prompt_only", "schema"], default="both")
    parser.add_argument("--limit", type=int, help="Kisa test icin ornek sayisi; varsayilan tumu")
    args = parser.parse_args()
    samples = load_dataset()
    if args.action == "prepare-gold":
        prepare_gold(samples)
        return
    limit = len(samples) if args.limit is None else args.limit
    if not 1 <= limit <= len(samples):
        parser.error(f"--limit 1 ile {len(samples)} arasinda olmali")
    gold, warning = read_gold(samples)
    if warning:
        print(warning)
    modes = ["prompt_only", "schema"] if args.mode == "both" else [args.mode]
    all_records = {}
    for mode in modes:
        if args.action == "run":
            all_records[mode] = run_mode(mode, samples, limit, gold)
        else:
            folder = FOLDER / mode
            records = load_records(folder / "predictions.jsonl")
            if not records:
                print(f"{mode}: henuz kaydedilmis tahmin yok.")
                continue
            summary = summarize([records[i] for i in sorted(records)], gold)
            write_json(folder / "summary.json", summary)
            all_records[mode] = records
            print(mode, json.dumps(summary, ensure_ascii=False, indent=2))
    if len(all_records) == 2:
        common = sorted(set(all_records["prompt_only"]) & set(all_records["schema"]))
        comparison = {"shared_sample_count": len(common),
                      "settings": "Same data, prompt, model and generation options; format differs.",
                      "prompt_only": summarize([all_records["prompt_only"][i] for i in common], gold),
                      "schema": summarize([all_records["schema"][i] for i in common], gold)}
        write_json(FOLDER / "comparison.json", comparison)
        print(f"Karsilastirma kaydedildi: {FOLDER / 'comparison.json'} ({len(common)} ortak ornek)")


if __name__ == "__main__":
    main()
