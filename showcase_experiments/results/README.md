# Showcase Experiments

- **01_temperature.md:** Qwen3:4B, JSON Schema; temperature 0 / 0.5 / 1.
- **02_model.md:** temperature 0, JSON Schema; Qwen3:4B / Qwen3:0.6B.
- **03_json_schema.md:** Qwen3:4B, temperature 0; schema / sadece prompt.

Tüm koşullarda aynı 120 haber, prompt, system rolü, seed=42, think=False, num_predict=4096.
Referans `base_4b_t0_schema` üç karşılaştırmada ortak kullanılır.
Her klasörde prompt ve config kaydı; JSONL, CSV, errors, analysis, confusion_matrix bulunur.
