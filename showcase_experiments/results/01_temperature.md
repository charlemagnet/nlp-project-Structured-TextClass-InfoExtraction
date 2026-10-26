# 01_temperature

Değişen tek ayar: temperature (0, 0.5, 1).

Karşılaştırılan ortak haber sayısı: **5**
Her grupta yalnızca adındaki parametre değişiyor; diğerleri sabit.

| Koşul | Doğru | Yanlış | Accuracy | Ham JSON | Şema |
|---|---:|---:|---:|---:|---:|
| base_4b_t0_schema | 0 | 5 | %0.00 | 5/5 | 5/5 |
| temp_05 | 0 | 5 | %0.00 | 5/5 | 5/5 |
| temp_1 | 0 | 5 | %0.00 | 5/5 | 5/5 |

## temp_05 vs base_4b_t0_schema
Yeni doğru olanlar (0): []
Önceden doğruyken yanlış olanlar (0): []

## temp_1 vs base_4b_t0_schema
Yeni doğru olanlar (0): []
Önceden doğruyken yanlış olanlar (0): []

Ham JSON başarısı, JSON temizliği öncesinde ölçülür.
Olası hata nedenleri için her koşulun errors.csv ve analysis.md dosyalarını incele.
