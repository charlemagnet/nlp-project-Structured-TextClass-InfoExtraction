import json
import re

# Allowed news categories
CATEGORIES = ["World", "Sports", "Business", "Sci/Tech"]

# Required JSON fields
REQUİRED_KEYS = {
    "category",
    "persons",
    "organizations",
    "locations"
}

def validate_schema(data):
    #JSON root must b(e a dictionary
    if not isinstance(data, dict):
        return False
    
    # Check required fields
    if set(data.keys()) != REQUİRED_KEYS:
        return False

    # Check category
    if data["category"] not in CATEGORIES:
        return False

    # Check entity lists
    for key in("persons", "organizations", "locations"):

        if not isinstance(data[key], list):
            return False

        for entitiy in data[key]:
            if not isinstance(entitiy, str):
                return False

    return True

def clean_response(text):
    # Remove inline thinking section, if present
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[-1]

    text = text.strip()

    # Extract the last Markdown code block if present
    blocks = re.findall(
        r"'''(?:json)?\s*(.*?)'''",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    if blocks:
        text = blocks[-1].strip()

    return text

def parse_llm_output(raw_text):

    result = {

        "raw_json_success": False,
        "recovered_json_success": False,
        "schema_valid": False,
        "method": None,
        "data": None,
        "first_error": None
    }

    try:
        parsed = json.loads(raw_text)

        result["raw_json_success"] = True
        result["method"] = "raw"
        result["data"] = parsed
        result["schema_valid"] = validate_schema(parsed)

        return result

    except (json.JSONDecodeError, TypeError) as error:
        result["first_error"] = str(error)

    # Step 2 Clean the response
    text = clean_response(raw_text if isinstance(raw_text, str)else "")

    try:
        parsed = json.loads(text)

    except json.JSONDecodeError:

        # Step 3: Try extracting JSON after introductory text
        start = text.find("{")

        if start == -1:
            return result

        try:
            decoder = json.JSONDecoder()
            parsed, end = decoder.raw_decode(text[start:])

        except json.JSONDecodeError:
            return result

    # Step 4: Store recovery result
    result["recovered_json_success"] = True
    result["method"] = "cleaned"
    result["data"] = parsed
    result["schema_valid"] = validate_schema(parsed)

    return result
    





    