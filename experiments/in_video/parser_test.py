"""parse_output fonksiyonunun ilk deneme sonucunu tek bir ornekle gosterir."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from core.main import parse_output

raw = '{"category":"Sports","persons":[],"organizations":[],"locations":[]}'
data, first_try = parse_output(raw)

print("Ham JSON:", raw)
print("Okunan veri:", json.dumps(data, ensure_ascii=False))
print("Ilk denemede JSON basarili mi?", first_try)
