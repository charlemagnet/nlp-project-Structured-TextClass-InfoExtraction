# Structured Text Classification and Information Extraction

This project uses a local, open-weight language model to classify news articles and extract named entities as machine-readable JSON. It was developed for NLP Project I using Python and Ollama; inference does not use a cloud LLM API.

**[Watch the video presentation](https://www.youtube.com/watch?v=XH9RLicW_4A)** · **[Technical report (PDF)](report/Project_I_Technical_Report.pdf)** · [Project instructions](https://uorhan.github.io/files/NLP-Project-1/)

## Task and data

The evaluation set consists of 120 English articles selected from the test split of [AG News](https://huggingface.co/datasets/fancyzhx/ag_news), with 30 examples in each class: World, Sports, Business, and Sci/Tech. The model predicts a class and extracts people, organizations, and locations. For example, the required JSON structure is:

```json
{
  "category": "Sports",
  "persons": [],
  "organizations": [],
  "locations": []
}
```

The classification label is withheld from the model and used only in evaluation. AG News does not provide entity labels for these samples. The entity reference file was drafted with AI assistance and reviewed by the student. Some model predictions were consulted while checking the labels, so they are **not an independent, blind annotation**; this limits the interpretation of entity F1.

## Main comparison

The same 120 articles and prompt were evaluated with `qwen3:4b-instruct-2507-q4_K_M` in two settings:

1. **Prompt-only:** the prompt asks for JSON; no Ollama `format` parameter is supplied.
2. **Schema-constrained:** a Pydantic JSON Schema is supplied through Ollama `format`.

The recorded comparison used Ollama 0.35.1, temperature 0, seed 42, `num_predict=1024`, `num_ctx=4096`, `think=false`, and `stream=false`. Other generation parameters were not explicitly set or captured in the experiment snapshots.

| Metric | Prompt-only | JSON Schema |
|---|---:|---:|
| Raw JSON parsing | 120/120 (100%) | 120/120 (100%) |
| Parsing after cleaning | 120/120 (100%) | 120/120 (100%) |
| Structural validity | 100% | 100% |
| Classification accuracy | 92/120 (76.67%) | 91/120 (75.83%) |
| Entity precision, micro | 80.07% | 74.06% |
| Entity recall, micro | 56.54% | 58.52% |
| Entity F1, micro | 66.28% | 65.38% |

Entity matching is exact and case-sensitive, within the same article and entity type. Duplicate identical strings within an article and type are counted once. A structurally invalid output is treated as an empty entity prediction. F1 aggregates true positives, false positives, and false negatives across the three types. These results use the reference-label snapshot identified in the [comparison file](experiments/19-11-26/comparison.json).

Both settings produced valid raw JSON in this comparison; the schema did not improve the format rate on this sample. Accuracy and entity F1 differed slightly. A schema can constrain output structure without guaranteeing that a category or entity is correct. A later live schema/temperature-0 run produced 92 correct classifications rather than 91; the small difference between runs should not be interpreted as a guaranteed effect of the schema.

## Setup and execution

The recorded environment used Python 3.13.1 and Ollama 0.35.1. Install Ollama and the local model, then create a virtual environment and install the dependencies. The commands below are for Windows CMD:

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
ollama pull qwen3:4b-instruct-2507-q4_K_M
```

The dataset and labels are already included. To inspect the 120-sample comparison and recompute its summary metrics from the saved predictions:

```cmd
python experiments\19-11-26\deney.py report
```

This command recalculates and writes the summary files and `comparison.json`; do not run it on a submitted snapshot that must remain unchanged. To run or resume the benchmark, use `python experiments\19-11-26\deney.py run`; existing snapshots are resumed only when their recorded settings and prompt match.

For the live demonstration, each command evaluates the same 120 articles followed by five new synthetic examples. A new `experiments/in_video/runN` folder is created for each invocation; previous runs are not overwritten.

```cmd
python experiments\in_video\run.py -mode prompt-only -temperature 0
python experiments\in_video\run.py -mode schema -temperature 0
python experiments\in_video\run.py -mode prompt-only -temperature 1
python experiments\in_video\run.py -mode schema -temperature 1
```

The five new examples are written directly in `experiments/in_video/run.py`; their informal expected categories are not sent to the model. Live-run accuracy is reported for the original 120 articles only. The live script does not calculate entity F1. The recorded live runs are in `experiments/in_video/run1` through `run4`.

## Repository guide

| Path | Purpose |
|---|---|
| `core/main.py` | Shared prompt and model settings; raw parsing, recovery, structure validation, and standalone prompt-only evaluation. |
| `core/schemas.py` | Pydantic definition used to build the constrained JSON Schema. |
| `data/evaluation_samples.json` | Balanced 120-article evaluation set. |
| `data/gold_labels.json` | Reference entity labels, matched after inference. |
| `experiments/19-11-26/deney.py` | Two-setting evaluation and entity F1 calculation. |
| `experiments/19-11-26/prompt_only/` and `schema/` | Saved settings, prompts, raw responses, and summaries for the main comparison. |
| `experiments/in_video/run.py` | Re-runnable live demonstration with the original articles and five new examples. |
| `experiments/in_video/structure_test.py` | Demonstration of the category-validation line. |
| `results/` | Earlier runs and comparisons, including the 0.6B/4B model-size comparison. |
| `evaluate.py`, `report_results.py` | Earlier modular evaluation and reporting workflow. |

Prior runs can use different model tags, prompts, and output settings. Their metrics should not be treated as a controlled comparison of schema alone. The 0.6B and 4B runs, for example, use different model variants; the 8B model was not evaluated.
