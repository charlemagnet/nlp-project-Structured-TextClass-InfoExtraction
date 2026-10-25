import pandas as pd
from llm_client import load_samples

# Load evaluation results and original news
results = pd.read_csv("results/results.csv")
dataset = load_samples()

# Select misclassified SCI/Tech articles
errors = results[
    (results["expected_category"] == "Sci/Tech")
    & (results["category_correct"] == False)
]

print("Misclassified Sci/Tech articles: ", len(errors))

for _, row in errors.iterrows():

    sample_id = int(row["sample_id"])
    article = dataset[sample_id]["text"]

    print("\n" + "-" * 60)
    print("Sample ID:", sample_id)
    print("Expected:", row["expected_category"])
    print("Predicted:", row["predicted_category"])
    print("Article:", article)