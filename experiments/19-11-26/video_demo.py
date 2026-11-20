"""Videoda ayni yeni haberleri iki format ve sicaklik ayariyla canli gosterir."""
import argparse
import inspect
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ollama import chat
from core.main import (DATA, MODEL, NUM_CTX, NUM_PREDICT, PROMPT, SEED,
                       parse_output, valid_structure)
from core.schemas import NewsAnalysis

# These are invented examples, not reports of real events. Expected categories
# are informal human judgments for discussion, not an annotated test set.
EXAMPLES = [
    ("World", "The governments of Canada and Norway signed a climate cooperation agreement in Oslo."),
    ("Sports", "The Ankara Falcons defeated the Izmir Tigers 3-1 in a football match in Istanbul."),
    ("Business", "Atlas Foods reported a 12 percent rise in quarterly revenue after opening stores in Berlin."),
    ("Sci/Tech", "Researchers at Delft University of Technology developed a battery that charges in five minutes."),
    ("Business", "Atlas Football Club announced that it will buy a cybersecurity company for five billion dollars, causing its shares to rise 20 percent."),
]


def demonstrate_line_removal():
    # Work on an in-memory copy of the actual function; never edit core/main.py.
    original_source = inspect.getsource(parse_output)
    line = "return json.loads(text), True"
    if original_source.count(line) != 1:
        raise RuntimeError("The original parsing line changed; inspect the code before this demonstration.")
    # A try block cannot be empty, so 'pass' keeps the copy syntactically valid.
    modified_source = original_source.replace(line, "pass  # parsing line removed")
    namespace = {"json": json, "re": re}
    exec(modified_source, namespace)
    example = '{"category":"Sports","persons":[],"organizations":[],"locations":[]}'
    normal_data, normal_first = parse_output(example)
    changed_data, changed_first = namespace["parse_output"](example)
    print("Actual line:", line)
    print("Copy with line removed: pass  # required to keep the try block valid")
    print("Input:", example)
    print("Original function:", normal_data, "first_try =", normal_first)
    print("Modified copy:   ", changed_data, "first_try =", changed_first)
    print("The JSON is still recovered, but the first-try measurement becomes false.")
    print("core/main.py was not changed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["prompt-only", "schema"], default="prompt-only")
    parser.add_argument("--temperature", type=float, choices=[0.0, 1.0], default=0.0)
    parser.add_argument("--test-line", action="store_true", help="Show the effect of removing the first parsing line")
    args = parser.parse_args()

    if args.test_line:
        demonstrate_line_removal()
        return

    samples = json.loads(DATA.read_text(encoding="utf-8"))
    known = {sample["text"].strip() for sample in samples}
    if any(text.strip() in known for _, text in EXAMPLES):
        raise SystemExit("A demo text is already in the evaluation dataset; choose a new example.")

    print("NEW SYNTHETIC EXAMPLES; expected categories are informal judgments.", flush=True)
    print(f"Model: {MODEL} | Mode: {args.mode} | Temperature: {args.temperature}", flush=True)
    print(f"seed={SEED}, num_predict={NUM_PREDICT}, num_ctx={NUM_CTX}, think=False", flush=True)
    for index, (expected, text) in enumerate(EXAMPLES, 1):
        request = {
            "model": MODEL,
            "messages": [{"role": "system", "content": PROMPT},
                         {"role": "user", "content": text}],
            "think": False,
            "stream": False,
            "options": {"temperature": args.temperature, "seed": SEED,
                        "num_predict": NUM_PREDICT, "num_ctx": NUM_CTX},
        }
        if args.mode == "schema":
            request["format"] = NewsAnalysis.model_json_schema()
        print(f"\n--- Sample {index}/5 ---", flush=True)
        print("Text:", text, flush=True)
        print("Expected category (informal):", expected, flush=True)
        if index == 5:
            print("Challenging case: the model may choose the wrong category or treat the generic", flush=True)
            print("phrase 'a cybersecurity company' as the name of an organization.", flush=True)
        try:
            response = chat(**request)
            raw = response.message.content or ""
            parsed, first_try = parse_output(raw)
            print("Raw model response:", raw, flush=True)
            print("Raw JSON success:", first_try, "| Structure valid:", valid_structure(parsed), flush=True)
            print("Parsed output:", json.dumps(parsed, ensure_ascii=False), flush=True)
        except Exception as error:
            print(f"Ollama error: {type(error).__name__}: {error}", flush=True)
            raise SystemExit(1) from error
    print("\nLive demo complete. No evaluation results were overwritten.", flush=True)


if __name__ == "__main__":
    main()
