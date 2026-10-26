# 02_model

Değişen tek ayar: model (4B, 0.6B).

Karşılaştırılan ortak haber sayısı: **5**
Her grupta yalnızca adındaki parametre değişiyor; diğerleri sabit.

| Koşul | Doğru | Yanlış | Accuracy | Ham JSON | Şema |
|---|---:|---:|---:|---:|---:|
| base_4b_t0_schema | 0 | 5 | %0.00 | 5/5 | 5/5 |
| model_06b | 2 | 3 | %40.00 | 5/5 | 5/5 |

## model_06b vs base_4b_t0_schema
Yeni doğru olanlar (2): [0, 1]
Önceden doğruyken yanlış olanlar (0): []

Ham JSON başarısı, JSON temizliği öncesinde ölçülür.
Olası hata nedenleri için her koşulun errors.csv ve analysis.md dosyalarını incele.
