# Live video experiments

`run.py` sends the same 120 AG News evaluation articles followed by five new synthetic examples to the local model. Each invocation creates a new `runN` directory without overwriting existing runs. The examples are defined in the `SAMPLES` list; the script checks that none matches the evaluation dataset after whitespace and case normalization.

The fifth synthetic text deliberately mixes sports, business, and technology. One possible error is extracting the generic phrase `a cybersecurity company` as a named organization. The actual response should be inspected rather than assuming the model will make that error.

## Windows CMD commands

From the repository root, with the virtual environment and Ollama active:

```cmd
.venv\Scripts\python.exe -B experiments\in_video\run.py -mode prompt-only -temperature 0
.venv\Scripts\python.exe -B experiments\in_video\run.py -mode schema -temperature 0
.venv\Scripts\python.exe -B experiments\in_video\run.py -mode prompt-only -temperature 1
.venv\Scripts\python.exe -B experiments\in_video\run.py -mode schema -temperature 1
```

Prompt-only does not send Ollama's `format` parameter; schema mode sends a JSON Schema. Temperature is the additional changed generation setting. `--mode` and `--temperature` are also accepted. Each command runs the same 120 + 5 texts; all four commands make 500 model calls.

The main 120-sample benchmark used temperature 0; temperature 1 is an additional live-test condition. The other settings come from `core/main.py`.

## Saved results

Each invocation creates the first available `runN` directory. A failed run is retained, and subsequent runs use a different number. Each run contains:

- `config.json`: model, format, temperature and other settings; schema when used.
- `samples.json`: dataset and synthetic texts with their source and expected categories.
- `prompt.txt`: the prompt sent to the model.
- `predictions.jsonl`: raw and parsed responses, validation results and any error.
- `summary.json`: completion, JSON and structure counts, accuracy on dataset articles, and processing status of the five new texts.

Expected categories are not sent to the model. The 120 dataset articles use their original class labels; expected categories for the five synthetic examples are informal and are not included in the accuracy calculation. Each prediction identifies its source. This script does not compute entity F1; see the earlier comparison in `experiments/19-11-26`.

`structure_test.py` supplies an invalid category to `valid_structure()` for the code-line demonstration. `Music` is rejected when the allowed-category check is present and accepted if that line is removed. Restore the line after the demonstration.
