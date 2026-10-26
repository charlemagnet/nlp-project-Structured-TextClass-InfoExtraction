from datasets import load_dataset

# Load the test dataset
dataset = load_dataset("fancyzhx/ag_news", split = "test")

# Print dataset info
print("Total samples:", len(dataset))

# Get category names
labels = dataset.features["label"].names
print("Categories", labels)

# Display first 5 samples
for i in range(5):
    sample = dataset[i]

    print("-"*40)
    print("Text:", sample["text"])
    print("Label ID:", sample["label"])
    print("Category:", labels[sample["label"]])