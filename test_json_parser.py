
import json
from pathlib import Path
from json_parser import parse_llm_output

# Create an example of valid JSON
valid_data = {
    "category": "Sports",
    "persons": ["Messi"],
    "organizations": [],
    "locations": []
}

valid_json = json.dumps(valid_data)

# Different output scenarios
test_cases = {
    "01_valid_json": valid_json,

    "02_markdown": (
        "```json\n" + valid_json + "\n```"
    ),

    "03_explanation": (
        "Here is your JSON:\n" + valid_json
    ),

    "04_thinking": (
        "Let me analyze this article...\n"
        "</think>\n" + valid_json
    ),

    "05_invalid_json": (
        '{"category": "Sports", "persons": ['
    )
}

print("=== CONTROLLED TESTS ===")

for name, text in test_cases.items():

    result = parse_llm_output(text)

    print(f"\n{name}")
    print("Raw success:", result["raw_json_success"])
    print("Recovery success:", result["recovered_json_success"])
    print("Schema valid:", result["schema_valid"])
    print("Method:", result["method"])


# Test saved outputs from the role experiment
output_dir = (
    Path(__file__).resolve().parent
    / "experiments"
    / "role_change"
    / "outputs"
)

experiment_names = [
    "01_user_think_false",
    "02_user_think_true",
    "03_system_think_false",
    "04_system_think_true"
]

print("\n=== SAVED LLM OUTPUTS ===")

for name in experiment_names:

    file_path = output_dir / name / "content.txt"

    if not file_path.exists():
        print(name, "- File not found")
        continue

    text = file_path.read_text(encoding="utf-8")

    result = parse_llm_output(text)

    print(f"\n{name}")
    print("Raw success:", result["raw_json_success"])
    print("Recovery success:", result["recovered_json_success"])
    print("Schema valid:", result["schema_valid"])
    print("Method:", result["method"])

    if result["data"] is not None:
        if isinstance(result["data"], dict):
            print("Category:", result["data"].get("category"))
