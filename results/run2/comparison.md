# run1 vs run2

Shared samples: 120

All metrics below use only shared sample IDs.

| Metric | Previous | Current |
|---|---:|---:|
| Accuracy | 83.33% | 76.67% |
| Raw JSON success | 120/120 | 120/120 |

Newly correct (7): [9, 53, 75, 76, 93, 101, 118]

Regressions (15): [3, 4, 12, 13, 21, 29, 38, 55, 61, 64, 78, 85, 89, 91, 114]

## Configuration Changes

- dataset_sha256: None -> dc8ecf52e176cbef8bab9b346a0400b3ce7ee1e4dde0a9b8a6e1839ec25a4d7c
- dataset_size: None -> 120
- format: None -> json_schema
- instruction_role: None -> system
- model: None -> qwen3:4b
- options: None -> {'temperature': 0, 'seed': 42, 'num_predict': 4096}
- prompt_version: None -> v2_category_definitions
- think: None -> False

Full prompt changes: prompt_diff.md
