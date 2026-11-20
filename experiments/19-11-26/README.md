# Deney günlüğü — 19.11.2026

## Amaç

Aynı 120 haber, model, prompt ve üretim ayarlarıyla iki yöntemi karşılaştırmak:

1. **prompt_only:** JSON sadece prompt ile istenir; Ollama çağrısına `format` verilmez.
2. **schema:** Aynı istek `format` içinde JSON Schema ile gönderilir.

Tek planlı fark `format` ayarıdır. Model ve ayarlar `core/main.py` dosyasından alınır. Her koşulun klasöründe ayar, prompt, ham yanıtlar ve özet tutulur; aynı ayarlarla yarıda kalan deney devam ettirilebilir. Ayarlar değişmişse eski deneyin üstüne yazılmaz.

## Metrikler

- **Ham JSON:** Temizlemeden önce doğrudan `json.loads` başarısı / toplam.
- **Temizlik sonrası JSON:** Ham hâlde okunanlar + yalnızca temizlikle kurtarılanlar / toplam.
- **Yapısal geçerlilik:** Gerekli dört alanın, kategori ve veri tiplerinin uygunluğu / toplam.
- **Sınıflandırma accuracy:** Yapısı geçerli ve kategorisi doğru cevaplar / toplam.
- **Entity micro precision, recall ve F1:** `data/gold_labels.json` içindeki referans varlık etiketlerine göre hesaplanır. Her örnekte ve her varlık türünde tekrar eden aynı metin tek varlık sayılır. Eşleşme, tür ve metin bakımından **tam ve büyük/küçük harfe duyarlı** olmalıdır. Geçersiz yapı, o örnekte boş tahmin sayılır. Hiç tahmin veya gold varlık yoksa ilgili sıfır paydalı metrik 0 kabul edilir.

Entity puanları 0–1 aralığındadır; diğer oranlar yüzdedir. F1 için değerlendirilen bütün örneklerin elle etiketlenmesi gerekir. Eksik etiket varken F1 `null` kalır; bu, sıfır performans anlamına gelmez.

## Entity etiketleme

`data/gold_labels.json` veri setindeki haberleri ve üç varlık alanını içerir. Referans etiketler Codex tarafından hazırlandı; hazırlanırken bazı model tahminleri kontrol amacıyla görüldü ve etiketler henüz insan tarafından doğrulanmadı. Bu nedenle F1 sonuçları ön değerlendirmedir. Etiketlerin hazırlanış biçimi ve sınır durumlar `data/gold_labels_notlari.md` dosyasında açıklanır. Her haber için metinde **açıkça geçen** kişi, kurum ve konum adları, metindeki yazımıyla ilgili listede olmalıdır.

- `null`: Henüz etiketlenmedi.
- `[]`: İncelendi ve o türden varlık bulunmadı.
- `["Microsoft", "OpenAI"]`: İncelendi ve bu iki kurum bulundu.

Sınır durumlarda aynı kuralları bütün haberlerde tutarlı uygulayın ve raporda açıklayın. Referans etiketler insan tarafından incelenmelidir. `text` ve `sample_id` alanlarını değiştirmeyin. Ek yerleştirme, alt dize veya yazım farkı eşleşme sayılmaz.

## Windows CMD komutları

Proje kök klasöründen:

```cmd
.venv\Scripts\python.exe experiments\19-11-26\deney.py run
```

Varsayılan olarak her iki koşul ve 120 örnek kullanılır. Kısa deneme için `run --limit 5` kullanılabilir; sonradan aynı komut `--limit` olmadan çalıştırıldığında eksik örneklerden devam eder. Ancak 5 örnek, hocanın en az 100 örnek şartını karşılamaz.

Referans etiketleri güncelledikten sonra, modeli yeniden çalıştırmadan F1 ve karşılaştırmayı güncellemek için:

```cmd
.venv\Scripts\python.exe experiments\19-11-26\deney.py report
```

Karşılaştırma `comparison.json` içinde yalnızca iki koşulun **ortak örnekleri** üzerinden hesaplanır. Her koşulun kendi `summary.json` dosyası, o koşulda kaydedilmiş bütün örnekleri kapsar.

## Kayıtlar

- `data/gold_labels.json`: Değerlendirmede kullanılan referans etiketler. Eski `gold_entities.json` bir boş taslaktır ve artık değerlendirmede kullanılmaz.
- `prompt_only/` ve `schema/`: Her koşulun ayarları ve sonuçları; deney çalıştıkça oluşur.
- `comparison.json`: İki koşulun ortak örnekler üzerindeki karşılaştırması; iki sonuç oluşunca yazılır.

## 19.11.2026 — 120 haberlik karşılaştırma

Model: `qwen3:4b-instruct-2507-q4_K_M`; Ollama 0.35.1; temperature 0; seed 42; `num_predict` 1024; `num_ctx` 4096; `think=False`. Aynı 120 örnek ve aynı prompt kullanıldı.

| Metrik | Prompt-only | JSON Schema |
|---|---:|---:|
| Haber sayısı | 120 | 120 |
| Ham JSON başarısı | 120/120 (%100) | 120/120 (%100) |
| Temizlik sonrası toplam JSON başarısı | 120/120 (%100) | 120/120 (%100) |
| Yalnızca temizlikle kurtarılan | 0 | 0 |
| Yapısal geçerlilik | %100 | %100 |
| Doğru sınıflandırma | 92/120 (%76,67) | 91/120 (%75,83) |
| Entity precision (micro) | %80,07 | %74,06 |
| Entity recall (micro) | %56,54 | %58,52 |
| Entity F1 (micro) | %66,28 | %65,38 |

Kategori tahmini yalnızca bir haberde değişti. Ayrıştırılmış JSON içeriği 54 haberde farklıydı; bu, kategori dışındaki entity alanlarının da değişebildiğini gösterir. İlk ayarda zaten bütün ham yanıtlar okunabildiği için bu örneklemde şema JSON başarısını artırmadı.

Entity F1 hesabında prompt-only için TP=229, FP=57, FN=176; schema için TP=237, FP=83, FN=168. Schema daha fazla doğru eşleşme buldu ama daha fazla yanlış eşleşme de üretti; bu eşleştirme ve referanslarla F1 0,90 yüzde puan daha düşük oldu. Kişi, kurum ve konuma göre ayrıntılar `comparison.json` içindedir. Bu bulguların yorumunda referans etiketlerin AI tarafından hazırlanıp tahminlerle kontrol edildiği ve henüz insan doğrulaması yapılmadığı göz önünde bulundurulmalıdır.
