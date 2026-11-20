"""Test whether an unexpected category passes the structure check."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from core.main import valid_structure

sample = {
    "category": "Music",
    "persons": [],
    "organizations": [],
    "locations": [],
}

print("Category:", sample["category"])
print("Structure valid?", valid_structure(sample))
