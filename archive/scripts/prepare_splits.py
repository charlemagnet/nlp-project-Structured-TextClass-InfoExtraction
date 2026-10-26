
import json
import random
import hashlib

from pathlib import Path
from collections import Counter
from datasets import load_dataset


DATA_DIR = Path(__file__).resolve().parent / "data"

OLD_FILE = DATA_DIR / "evaluation_samples.json"
DEV_FILE = DATA_DIR / "development_samples.json"
FINAL_FILE = DATA_DIR / "final_test_samples.json"
MANIFEST_FILE = DATA_DIR / "dataset_manifest.json"

CATEGORIES = ["World", "Sports", "Business", "Sci/Tech"]


# Create an identifier based on article content
def article_hash(text):

    normalized = " ".join(text.casefold().split())

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


# Select a balanced dataset
def select_balanced(source, per_category, seed, used_hashes):

    groups = {label: [] for label in range(4)}

    for sample in source:
        groups[sample["label"]].append(sample)

    rng = random.Random(seed)
    selected = []

    for label_id, category in enumerate(CATEGORIES):

        candidates = groups[label_id].copy()
        rng.shuffle(candidates)

        count = 0

        for sample in candidates:

            fingerprint = article_hash(sample["text"])

            # Skip previously used or duplicate articles
            if fingerprint in used_hashes:
                continue

            selected.append({
                "text": sample["text"],
                "label": sample["label"]
            })

            used_hashes.add(fingerprint)
            count += 1

            if count == per_category:
                break

        if count != per_category:
            raise ValueError(
                f"Not enough unique articles for {category}"
            )

    rng.shuffle(selected)

    return selected


def save_dataset(path, samples):

    path.write_text(
        json.dumps(
            samples,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )


def file_sha256(path):

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def print_counts(name, samples):

    counts = Counter(
        sample["label"] for sample in samples
    )

    print(f"\n{name}: {len(samples)} articles")

    for label_id, category in enumerate(CATEGORIES):
        print(f"{category}: {counts[label_id]}")


def main():

    # Protect previously evaluated articles
    old_samples = json.loads(
        OLD_FILE.read_text(encoding="utf-8")
    )

    used_hashes = {
        article_hash(sample["text"])
        for sample in old_samples
    }

    # Do not overwrite existing splits
    if DEV_FILE.exists() or FINAL_FILE.exists():
        raise FileExistsError(
            "Dataset splits already exist. "
            "Do not overwrite frozen datasets."
        )

    # Development set comes from training data
    train = load_dataset(
        "fancyzhx/ag_news",
        split="train"
    )

    development = select_balanced(
        train,
        per_category=20,
        seed=2026,
        used_hashes=used_hashes
    )

    save_dataset(DEV_FILE, development)

    # Final test comes from unused test articles
    test = load_dataset(
        "fancyzhx/ag_news",
        split="test"
    )

    final_test = select_balanced(
        test,
        per_category=30,
        seed=2027,
        used_hashes=used_hashes
    )

    save_dataset(FINAL_FILE, final_test)

    # Store dataset provenance and fingerprints
    manifest = {
        "source": "fancyzhx/ag_news",
        "old_evaluation": {
            "file": OLD_FILE.name,
            "split": "test",
            "samples": len(old_samples),
            "sha256": file_sha256(OLD_FILE)
        },
        "development": {
            "file": DEV_FILE.name,
            "split": "train",
            "seed": 2026,
            "samples": len(development),
            "sha256": file_sha256(DEV_FILE)
        },
        "final_test": {
            "file": FINAL_FILE.name,
            "split": "test",
            "seed": 2027,
            "samples": len(final_test),
            "sha256": file_sha256(FINAL_FILE)
        }
    }

    MANIFEST_FILE.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

    print_counts("OLD EVALUATION", old_samples)
    print_counts("DEVELOPMENT", development)
    print_counts("FINAL TEST", final_test)

    print("\nNo duplicate article texts selected.")
    print("Dataset manifest saved.")


if __name__ == "__main__":
    main()
