
import json
from pathlib import Path
from ollama import chat

# Project settings
PROJECT_DIR = Path(__file__).resolve().parent
DATA_FILE = PROJECT_DIR / "data" / "evaluation_samples.json"

MODEL = "qwen3:4b"

OPTIONS = {
    "temperature": 0,
    "seed": 42,
    "num_predict": 4096
}

# Instructions used for all news articles
TASK_INSTRUCTIONS = """
You are a news classification and named entity extraction system.

Tasks:
1. Classify the news article into exactly one category:
   World, Sports, Business, Sci/Tech.

2. Extract named entities:
   - persons
   - organizations
   - locations

Return only one valid JSON object with these keys:
{
    "category": "Business",
    "persons": [],
    "organizations": [],
    "locations": []
}

Use only the four allowed categories.
Extract only entities explicitly mentioned in the article.
If no entities are found, return an empty list.
Do not add explanations, markdown or extra text.
"""


# Load evaluation dataset
def load_samples():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# Build messages for Ollama
def build_messages(news_text, instruction_role="system"):

    if instruction_role not in ("system", "user"):
        raise ValueError("Instruction role must be system or user")

    return [
        {
            "role": instruction_role,
            "content": TASK_INSTRUCTIONS
        },
        {
            "role": "user",
            "content": f"News article:\n{news_text}"
        }
    ]


# Send news to the local LLM

def analyze_news(
    news_text,
    instruction_role="system",
    think=False,
    response_format=None
):
    messages = build_messages(news_text, instruction_role)

    response = chat(
        model=MODEL,
        messages=messages,
        think=think,
        format=response_format,
        stream=False,
        options=OPTIONS
    )

    return response

# Run directly for a quick test
if __name__ == "__main__":

    dataset = load_samples()
    sample = dataset[0]

    response = analyze_news(sample["text"])

    print("NEWS ARTICLE:")
    print(sample["text"])

    print("\nMODEL RESPONSE PREVIEW:")
    print((response.message.content or "")[:1000])

    print("\nSEPARATE THINKING:")
    print(bool(response.message.thinking))
