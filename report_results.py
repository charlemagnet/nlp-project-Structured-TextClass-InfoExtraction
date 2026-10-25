
import argparse
import csv
import difflib
import json

from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

from llm_client import load_samples


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

CATEGORIES = ["World", "Sports", "Business", "Sci/Tech"]


def read_csv(path):

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def is_true(value):
    return str(value).lower() == "true"


def accuracy(rows):

    if not rows:
        return 0.0

    correct = sum(
        is_true(r["category_correct"])
        for r in rows
    )

    return 100 * correct / len(rows)


def potential_reason(expected, predicted, article):

    text = article.lower()

    tech = [
        word for word in (
            "internet", "software", "science", "scientist",
            "research", "technology", "computer", "network",
            "worm", "playstation", "processor", "discover",
            "evolution", "web", "game console"
        )
        if word in text
    ]

    business = [
        word for word in (
            "market", "company", "acquisition",
            "earnings", "price", "sales", "cost",
            "cfo", "business"
        )
        if word in text
    ]

    world = [
        word for word in (
            "government", "trial", "police",
            "prosecut", "law", "japan", "peru",
            "court", "minister"
        )
        if word in text
    ]

    if expected == "Sci/Tech" and predicted == "World":
        reason = (
            "Possible overlap between science/technology "
            "and government, legal or international news."
        )

    elif expected == "Sci/Tech" and predicted == "Business":
        reason = (
            "Possible overlap between technology products "
            "and company, market or finance news."
        )

    elif expected == "World" and predicted == "Business":
        reason = (
            "Possible overlap between international "
            "affairs and commercial developments."
        )

    elif expected == "Business" and predicted == "World":
        reason = (
            "Possible overlap between economic activity "
            "and international affairs."
        )

    else:
        reason = (
            "Potentially ambiguous topic, incomplete "
            "article or dataset labeling convention."
        )

    clues = (tech[:2] + business[:2] + world[:2])[:5]

    if clues:
        reason += " Text clues: " + ", ".join(clues)

    else:
        reason += " Manual review recommended."

    return reason


def build_confusion(rows, path):

    columns = CATEGORIES + ["Invalid"]

    matrix = [
        [0 for _ in columns]
        for _ in CATEGORIES
    ]

    for row in rows:

        actual = row["expected_category"]
        predicted = row["predicted_category"]

        if actual not in CATEGORIES:
            continue

        if (
            is_true(row["schema_valid"])
            and predicted in CATEGORIES
        ):
            predicted_column = predicted
        else:
            predicted_column = "Invalid"

        i = CATEGORIES.index(actual)
        j = columns.index(predicted_column)

        matrix[i][j] += 1

    fig, ax = plt.subplots(figsize=(9, 6))

    im = ax.imshow(matrix, cmap="Blues", vmin=0)

    ax.set_xticks(range(len(columns)), columns)
    ax.set_yticks(range(len(CATEGORIES)), CATEGORIES)

    ax.set_xlabel("Predicted Category")
    ax.set_ylabel("Actual Category")

    ax.set_title(
        "Confusion Matrix - " + path.parent.name
    )

    max_value = max(max(row) for row in matrix)

    for i in range(len(CATEGORIES)):
        for j in range(len(columns)):

            value = matrix[i][j]

            color = (
                "white"
                if value > max_value / 2
                else "black"
            )

            ax.text(
                j, i, value,
                ha="center",
                va="center",
                color=color
            )

    fig.colorbar(im, ax=ax, label="Article Count")
    fig.tight_layout()

    fig.savefig(path, dpi=160)
    plt.close(fig)

    return matrix


def generate_report(run, compare=None):

    folder = RESULTS / run
    rows = read_csv(folder / "results.csv")

    if not rows:
        raise ValueError("No results found")

    dataset = load_samples()

    # Generate confusion matrix
    build_confusion(
        rows,
        folder / "confusion_matrix.png"
    )

    # Find misclassified articles
    mistakes = []

    for row in rows:

        if is_true(row["category_correct"]):
            continue

        sample_id = int(row["sample_id"])
        article = dataset[sample_id]["text"]

        mistakes.append({
            "sample_id": sample_id,
            "expected": row["expected_category"],
            "predicted": row["predicted_category"] or "Invalid",
            "article": article,
            "potential_reason": potential_reason(
                row["expected_category"],
                row["predicted_category"],
                article
            )
        })

    # Save error details
    with (folder / "errors.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:

        columns = [
            "sample_id", "expected", "predicted",
            "article", "potential_reason"
        ]

        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(mistakes)

    # Build analysis document
    lines = [
        f"# {run} Analysis",
        "",
        f"Samples: {len(rows)}",
        f"Accuracy: {accuracy(rows):.2f}%",
        f"Errors: {len(mistakes)}",
        "",
        "## Category Accuracy",
        "",
        "| Category | Correct / Total | Accuracy |",
        "|---|---:|---:|"
    ]

    for category in CATEGORIES:

        group = [
            r for r in rows
            if r["expected_category"] == category
        ]

        correct = sum(
            is_true(r["category_correct"])
            for r in group
        )

        if group:
            lines.append(
                f"| {category} | {correct}/{len(group)} "
                f"| {100 * correct / len(group):.2f}% |"
            )

    lines.extend([
        "",
        "## Confusion Matrix",
        "",
        "![Confusion Matrix](confusion_matrix.png)",
        "",
        "## Error Patterns",
        "",
        "| Actual -> Predicted | Count |",
        "|---|---:|"
    ])

    counts = Counter(
        (r["expected"], r["predicted"])
        for r in mistakes
    )

    for (actual, predicted), count in counts.most_common():
        lines.append(
            f"| {actual} -> {predicted} | {count} |"
        )

    lines.extend([
        "",
        "## Individual Errors",
        "",
        "Possible reasons are heuristic hypotheses, "
        "not verified explanations.",
        "",
        "| ID | Actual -> Predicted | Potential Reason |",
        "|---:|---|---|"
    ])

    for error in mistakes:
        lines.append(
            f"| {error['sample_id']} "
            f"| {error['expected']} -> {error['predicted']} "
            f"| {error['potential_reason']} |"
        )

    (folder / "analysis.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    # Compare with previous run
    if compare:

        old_folder = RESULTS / compare
        old_rows = read_csv(old_folder / "results.csv")

        old_map = {
            int(r["sample_id"]): r
            for r in old_rows
        }

        new_map = {
            int(r["sample_id"]): r
            for r in rows
        }

        shared = sorted(
            old_map.keys() & new_map.keys()
        )

        if not shared:
            raise ValueError(
                "Runs have no shared sample IDs."
            )

        for i in shared:
            if (
                old_map[i]["expected_category"]
                != new_map[i]["expected_category"]
            ):
                raise ValueError(
                    "Gold labels differ. Check dataset version."
                )

        before = [old_map[i] for i in shared]
        after = [new_map[i] for i in shared]

        improved = [
            i for i in shared
            if not is_true(old_map[i]["category_correct"])
            and is_true(new_map[i]["category_correct"])
        ]

        regressed = [
            i for i in shared
            if is_true(old_map[i]["category_correct"])
            and not is_true(new_map[i]["category_correct"])
        ]

        comparison = [
            f"# {compare} vs {run}",
            "",
            f"Shared samples: {len(shared)}",
            "",
            "All metrics below use only shared sample IDs.",
            "",
            "| Metric | Previous | Current |",
            "|---|---:|---:|",
            f"| Accuracy | {accuracy(before):.2f}% "
            f"| {accuracy(after):.2f}% |",
            f"| Raw JSON success | "
            f"{sum(is_true(r['raw_json_success']) for r in before)}"
            f"/{len(before)} | "
            f"{sum(is_true(r['raw_json_success']) for r in after)}"
            f"/{len(after)} |",
            "",
            f"Newly correct ({len(improved)}): {improved}",
            "",
            f"Regressions ({len(regressed)}): {regressed}",
            "",
            "## Configuration Changes",
            ""
        ]

        def read_config(directory):

            path = directory / "config.json"

            if path.exists():
                return json.loads(
                    path.read_text(encoding="utf-8")
                )

            return {}

        old_config = read_config(old_folder)
        new_config = read_config(folder)

        keys = sorted(
            old_config.keys() | new_config.keys()
        )

        for key in keys:

            old_value = old_config.get(key)
            new_value = new_config.get(key)

            if old_value != new_value:
                comparison.append(
                    f"- {key}: {old_value} -> {new_value}"
                )

        # Compare saved prompts
        old_prompt = old_folder / "prompt.txt"
        new_prompt = folder / "prompt.txt"

        if old_prompt.exists() and new_prompt.exists():

            diff = list(difflib.unified_diff(
                old_prompt.read_text(
                    encoding="utf-8"
                ).splitlines(),
                new_prompt.read_text(
                    encoding="utf-8"
                ).splitlines(),
                fromfile=f"{compare}/prompt",
                tofile=f"{run}/prompt",
                lineterm=""
            ))

            diff_text = "\n".join(
                diff or ["(Identical prompts)"]
            )

            (folder / "prompt_diff.md").write_text(
                "# Prompt Changes\n\n```diff\n"
                + diff_text
                + "\n```\n",
                encoding="utf-8"
            )

            comparison.append(
                "\nFull prompt changes: prompt_diff.md"
            )

        (folder / "comparison.md").write_text(
            "\n".join(comparison) + "\n",
            encoding="utf-8"
        )

    print("Reports created in:", folder)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--compare")

    args = parser.parse_args()

    generate_report(args.run, args.compare)
