# 03_json_schema

Değişen tek ayar: format (JSON Schema, yalnızca prompt).

Karşılaştırılan ortak haber sayısı: **5**
Her grupta yalnızca adındaki parametre değişiyor; diğerleri sabit.

| Koşul | Doğru | Yanlış | Accuracy | Ham JSON | Şema |
|---|---:|---:|---:|---:|---:|
| base_4b_t0_schema | 0 | 5 | %0.00 | 5/5 | 5/5 |
| no_schema | 3 | 2 | %60.00 | 0/5 | 5/5 |

## no_schema vs base_4b_t0_schema
Yeni doğru olanlar (3): [2, 3, 4]
Önceden doğruyken yanlış olanlar (0): []

Ham JSON başarısı, JSON temizliği öncesinde ölçülür.
Olası hata nedenleri için her koşulun errors.csv ve analysis.md dosyalarını incele.
