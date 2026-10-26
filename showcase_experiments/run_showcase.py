import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ollama import chat, show
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.llm_client import DATA_FILE
from core.prompts import TASK_INSTRUCTIONS
from core.json_parser import parse_llm_output
from core.schemas import NewsAnalysis

OUTPUT = Path(__file__).resolve().parent / 'results'
LABELS = ['World', 'Sports', 'Business', 'Sci/Tech']
CASES = {
    'base_4b_t0_schema': ('qwen3:4b', 0, True),
    'temp_05': ('qwen3:4b', 0.5, True),
    'temp_1': ('qwen3:4b', 1, True),
    'model_06b': ('qwen3:0.6b', 0, True),
    'no_schema': ('qwen3:4b', 0, False),
}
GROUPS = {
    '01_temperature': ('Değişen tek ayar: temperature (0, 0.5, 1).',
                       ['base_4b_t0_schema', 'temp_05', 'temp_1']),
    '02_model': ('Değişen tek ayar: model (4B, 0.6B).',
                 ['base_4b_t0_schema', 'model_06b']),
    '03_json_schema': ('Değişen tek ayar: format (JSON Schema, yalnızca prompt).',
                       ['base_4b_t0_schema', 'no_schema']),
}


def save_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def read_jsonl(path):
    if not path.exists():
        return {}
    return {r['id']: r for line in path.read_text(encoding='utf-8').splitlines()
            if line.strip() for r in [json.loads(line)]}


def run_one(index, sample, model, temperature, use_schema):
    row = dict(id=index, text=sample['text'], expected=LABELS[sample['label']],
               predicted=None, request_ok=False, raw_json=False, recovered=False,
               schema_valid=False, correct=False, raw_output='', parsed=None,
               error=None, done_reason=None, tokens=None, seconds=0)
    start = perf_counter()
    try:
        response = chat(
            model=model,
            messages=[{'role': 'system', 'content': TASK_INSTRUCTIONS},
                      {'role': 'user', 'content': 'News article:\n' + sample['text']}],
            format=NewsAnalysis.model_json_schema() if use_schema else None,
            think=False, stream=False,
            options={'temperature': temperature, 'seed': 42, 'num_predict': 4096}
        )
        row['request_ok'] = True
        row['raw_output'] = response.message.content or ''
        row['tokens'] = response.eval_count
        row['done_reason'] = response.done_reason
        parsed = parse_llm_output(row['raw_output'])
        row['raw_json'] = parsed['raw_json_success']
        row['recovered'] = parsed['recovered_json_success']
        row['parsed'] = parsed['data']
        if isinstance(parsed['data'], dict):
            row['predicted'] = parsed['data'].get('category')
            try:
                NewsAnalysis.model_validate(parsed['data'], strict=True)
                row['schema_valid'] = True
            except ValidationError as e:
                row['error'] = str(e)
        row['correct'] = row['schema_valid'] and row['predicted'] == row['expected']
    except Exception as e:
        row['error'] = f'{type(e).__name__}: {e}'
    finally:
        row['seconds'] = round(perf_counter() - start, 2)
    return row


def possible_reason(actual, pred):
    if pred == 'Invalid':
        return 'JSON/şema sorunu; ham yanıtı incele.'
    if actual == 'Sci/Tech' and pred == 'World':
        return 'Bilim/teknoloji konusu dünya gündemiyle karışmış olabilir.'
    if actual == 'Sci/Tech' and pred == 'Business':
        return 'Teknolojik ürün ve ticari faaliyet odağı karışmış olabilir.'
    if actual == 'Business' and pred == 'World':
        return 'Ekonomi ve uluslararası gelişme ayrımı belirsiz olabilir.'
    if actual == 'World' and pred == 'Business':
        return 'Uluslararası olay ve ticari boyut karışmış olabilir.'
    return 'Kısa/belirsiz haber veya kategori sınırı; elle incele.'


def write_case(folder, saved, limit):
    rows = [saved[i] for i in range(limit)]
    n = len(rows)
    correct = sum(r['correct'] for r in rows)
    raw = sum(r['raw_json'] for r in rows)
    valid = sum(r['schema_valid'] for r in rows)
    summary = {'total': n, 'correct': correct, 'wrong': n-correct,
               'accuracy': round(100*correct/n, 2),
               'raw_json': raw, 'raw_json_rate': round(100*raw/n, 2),
               'schema_valid': valid, 'schema_rate': round(100*valid/n, 2),
               'recovered': sum(r['recovered'] for r in rows),
               'request_failures': sum(not r['request_ok'] for r in rows),
               'average_seconds': round(sum(r['seconds'] for r in rows)/n, 2)}
    save_json(folder / 'summary.json', summary)
    fields = ['id', 'expected', 'predicted', 'correct', 'raw_json', 'recovered',
              'schema_valid', 'seconds', 'tokens', 'done_reason', 'error']
    with (folder / 'results.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r.get(k) for k in fields} for r in rows)
    mistakes = []
    matrix = [[0]*5 for _ in LABELS]  # 5th column: Invalid
    for r in rows:
        pred = r['predicted'] if r['schema_valid'] and r['predicted'] in LABELS else 'Invalid'
        matrix[LABELS.index(r['expected'])][(LABELS+['Invalid']).index(pred)] += 1
        if not r['correct']:
            mistakes.append(dict(id=r['id'], actual=r['expected'], predicted=pred,
                                 article=r['text'], possible_reason=possible_reason(r['expected'], pred),
                                 error=r['error'] or ''))
    with (folder / 'errors.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['id','actual','predicted','article','possible_reason','error'])
        writer.writeheader()
        writer.writerows(mistakes)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.imshow(matrix, cmap='Blues')
    ax.set_xticks(range(5), LABELS+['Invalid'])
    ax.set_yticks(range(4), LABELS)
    ax.set_xlabel('Predicted')
    ax.set_ylabel('Actual')
    ax.set_title(folder.name)
    for i in range(4):
        for j in range(5):
            ax.text(j, i, str(matrix[i][j]), ha='center', va='center')
    fig.tight_layout()
    fig.savefig(folder / 'confusion_matrix.png', dpi=160)
    plt.close(fig)
    lines = [f'# {folder.name}', '', f'**{correct}/{n} doğru**, **{n-correct} yanlış**, accuracy: **%{summary["accuracy"]}**',
             f'Ham JSON: {raw}/{n} | Şema uygun: {valid}/{n} | Temizlikle kurtarılan: {summary["recovered"]}',
             '', '## Kategori sonuçları', '', '| Kategori | Doğru / Toplam |', '|---|---:|']
    for cat in LABELS:
        subset = [r for r in rows if r['expected'] == cat]
        lines.append(f'| {cat} | {sum(r["correct"] for r in subset)}/{len(subset)} |')
    lines += ['', '## Confusion matrix', '![Confusion matrix](confusion_matrix.png)', '',
              '## Yanlış tahminler (nedenler doğrulanmış değil, hipotez)',
              '| ID | Gerçek → Tahmin | Olası sebep |', '|---:|---|---|']
    for e in mistakes:
        lines.append(f'| {e["id"]} | {e["actual"]} → {e["predicted"]} | {e["possible_reason"]} |')
    (folder / 'analysis.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return summary


def compare_groups():
    for report, (description, cases) in GROUPS.items():
        if any(not (OUTPUT / case / 'predictions.jsonl').exists() for case in cases):
            continue
        runs = {case: read_jsonl(OUTPUT / case / 'predictions.jsonl') for case in cases}
        ids = sorted(set.intersection(*(set(data) for data in runs.values())))
        if not ids:
            continue
        lines = [f'# {report}', '', description, '', f'Karşılaştırılan ortak haber sayısı: **{len(ids)}**',
                 'Her grupta yalnızca adındaki parametre değişiyor; diğerleri sabit.', '',
                 '| Koşul | Doğru | Yanlış | Accuracy | Ham JSON | Şema |',
                 '|---|---:|---:|---:|---:|---:|']
        base = runs[cases[0]]
        for case in cases:
            rows = [runs[case][i] for i in ids]
            n = len(rows)
            right = sum(r['correct'] for r in rows)
            lines.append(f'| {case} | {right} | {n-right} | %{100*right/n:.2f} | '
                         f'{sum(r["raw_json"] for r in rows)}/{n} | '
                         f'{sum(r["schema_valid"] for r in rows)}/{n} |')
        for case in cases[1:]:
            other = runs[case]
            fixed = [i for i in ids if not base[i]['correct'] and other[i]['correct']]
            lost = [i for i in ids if base[i]['correct'] and not other[i]['correct']]
            lines += ['', f'## {case} vs {cases[0]}',
                      f'Yeni doğru olanlar ({len(fixed)}): {fixed}',
                      f'Önceden doğruyken yanlış olanlar ({len(lost)}): {lost}']
        lines += ['', 'Ham JSON başarısı, JSON temizliği öncesinde ölçülür.',
                  'Olası hata nedenleri için her koşulun errors.csv ve analysis.md dosyalarını incele.']
        (OUTPUT / f'{report}.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--case', choices=['all']+list(CASES), default='all')
    args = parser.parse_args()
    dataset = json.loads(DATA_FILE.read_text(encoding='utf-8'))
    if not 1 <= args.limit <= len(dataset):
        parser.error('Geçersiz limit')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'README.md').write_text(
        '# Showcase Experiments\n\n'
        '- **01_temperature.md:** Qwen3:4B, JSON Schema; temperature 0 / 0.5 / 1.\n'
        '- **02_model.md:** temperature 0, JSON Schema; Qwen3:4B / Qwen3:0.6B.\n'
        '- **03_json_schema.md:** Qwen3:4B, temperature 0; schema / sadece prompt.\n\n'
        'Tüm koşullarda aynı 120 haber, prompt, system rolü, seed=42, think=False, num_predict=4096.\n'
        'Referans `base_4b_t0_schema` üç karşılaştırmada ortak kullanılır.\n'
        'Her klasörde prompt ve config kaydı; JSONL, CSV, errors, analysis, confusion_matrix bulunur.\n',
        encoding='utf-8')
    for name, (model, temp, schema) in CASES.items():
        if args.case != 'all' and name != args.case:
            continue
        folder = OUTPUT / name
        folder.mkdir(exist_ok=True)
        config = dict(model=model, temperature=temp, format='schema' if schema else 'prompt_only',
                      seed=42, think=False, num_predict=4096, role='system',
                      dataset_sha256=hashlib.sha256(DATA_FILE.read_bytes()).hexdigest(),
                      prompt_sha256=hashlib.sha256(TASK_INSTRUCTIONS.encode()).hexdigest())
        cfg_file, prompt_file = folder / 'config.json', folder / 'prompt.txt'
        if cfg_file.exists() and prompt_file.exists():
            if json.loads(cfg_file.read_text(encoding='utf-8')) != config or prompt_file.read_text(encoding='utf-8') != TASK_INSTRUCTIONS:
                raise RuntimeError(f'{name}: ayarlar değişmiş, eski sonuçlar korunuyor.')
        elif any(folder.iterdir()):
            raise RuntimeError(f'{name}: config eksik, sonuçlara dokunulmadı.')
        else:
            save_json(cfg_file, config)
            prompt_file.write_text(TASK_INSTRUCTIONS, encoding='utf-8')
        # Check model availability BEFORE saving predictions
        show(model)
        saved = read_jsonl(folder / 'predictions.jsonl')
        for i in range(args.limit):
            if i in saved:
                continue
            row = run_one(i, dataset[i], model, temp, schema)
            with (folder / 'predictions.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False)+'\n')
            saved[i] = row
            print(f'{name} [{i+1}/{args.limit}]: {row["expected"]} -> {row["predicted"]}, doğru={row["correct"]}')
        summary = write_case(folder, saved, args.limit)
        print(f'{name}: {summary["correct"]}/{summary["total"]} doğru; ham JSON {summary["raw_json"]}/{summary["total"]}')
        compare_groups()
    print('Raporlar:', OUTPUT)


if __name__ == '__main__':
    main()
