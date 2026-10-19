import json
import random
from pathlib import Path
from collections import Counter
from datasets import load_dataset

# Load dataset
dataset = load_dataset("fancyzhx/ag_news", split ="test")

# Get category names
labels = dataset.features["label"].names

# Select 30 samples from each category
selected_samples = []

for label_id, category in enumerate(labels):

    category_data = dataset.filter(
        lambda sample: sample["label"] == label_id
    )

    category_data = category_data.shuffle(seed=42)

    samples = category_data.select(range(30))

    selected_samples.extend(samples)

    print(f"{category}: {len(samples)} samples selected")

# Shuffle selected samples
random.Random(42).shuffle(selected_samples)

# Save to JSON
output_path = Path("data/evaluation_samples.json")

output_path.parent.mkdir(parents=True, exist_ok=True)

with output_path.open("w", encoding="utf-8",) as f:
    json.dump(selected_samples, f, indent=2, ensure_ascii=False)

# Verify dataset
counts = Counter(sample["label"] for sample in selected_samples)

print("\nTotal samples:", len(selected_samples))

for label_id, count in sorted(counts.items()):
    print(f"{labels[label_id]}: {count}")

print("\nDataset saved to:", output_path)