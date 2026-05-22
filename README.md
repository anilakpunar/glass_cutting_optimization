# Cam Kesim Optimizasyon Sistemi

Endustriyel cam kesim operasyonlari icin Google OR-Tools (CP-SAT)
tabanli, katmanli mimaride bir Python uygulamasi.

> **Yeni baslayanlar icin:** Optimizasyonun nasil calistigini basit bir
> ornek uzerinden adim adim ve gorsel olarak anlatan dokuman:
> [docs/nasil_calisir.md](docs/nasil_calisir.md)

## Ozellikler

- **Guillotine-kisitli kesim (varsayilan)**: Cam kesim koprusu duz
  (edge-to-edge) kestigi icin yerlesim guillotine kesilebilir uretilir:
  once boylu boyunca, sonra ara kesimler. Klasik bin-packing degil,
  guillotine 2D cutting-stock.
- **Homojen-blok yerlestirme**: Her plakaya once tek olcuden izgara
  dolusu, kalan artiklara sonraki olculer — boylece hem fire hem parca
  cesitliligi azaltilir.
- **CP-SAT 2D yerlestirme (alternatif)**: NoOverlap2D ile matematiksel
  olarak gecerli serbest cozumler; oncelik agirlikli amac fonksiyonu.
- **Coklu plaka orkestrasyonu**: Farkli boy ve cam tipindeki stoklar
  arasinda en-iyi-uygun secimi (best-fit) ile siralanir.
- **Kerf (testere kalinligi) ve kenar payi**: Endustriyel parametrelerle
  modellenir, gercek kesime hazir cikti uretir.
- **Rotasyon kisitlamalari**: Desenli / kaplamali cam icin grain
  kisitlamasi (`fixed`, `prefer_fixed`, `none`).
- **Cok cam tipi destegi**: Float, temperli, lamine, Low-E, ayna,
  desenli; her tip kendi stogu ile eslesir.
- **Maliyet & fire analizi**: Plaka birim maliyeti, hammadde, fire
  degeri, geri kullanilabilir offcut tespiti.
- **Operasyon plani**: Atolye operatoru icin sirali kesim talimatlari.
- **Gorsel cikti**: Her plaka icin matplotlib gorseli (ayni olcu ayni
  renk - homojenlik gorunur).
- **Web arayuzu**: Streamlit ile girdi girme, calistirma ve sonuc
  goruntuleme (bkz. asagi).
- **CLI + programatik API**: typer tabanli komut satiri ya da Python
  import ederek kullanim.

## Mimari (Katmanlar)

```
src/glass_optimizer/
├── domain/         # Veri modelleri (Pydantic)
│   ├── enums.py        # GlassType, GrainConstraint, CutOrientation
│   └── models.py       # StockSheet, PartOrder, Placement, Solution
├── data/           # I/O katmani
│   ├── loaders.py      # JSON / CSV yukleyiciler
│   └── validators.py   # Girdi dogrulamasi
├── optimization/   # Cozucu katmani
│   ├── base.py         # Strateji arayuzu
│   ├── cpsat_solver.py # Tek plaka CP-SAT modeli
│   └── multi_sheet.py  # Coklu plaka orkestrasyonu
├── services/       # Is mantigi katmani
│   ├── cost_calculator.py
│   ├── waste_analyzer.py
│   └── cutting_plan.py
├── presentation/   # Sunum katmani
│   ├── cli.py          # typer CLI
│   ├── reporter.py     # Konsol + metin rapor
│   └── visualizer.py   # matplotlib PNG
└── config/
    └── settings.py     # Cozucu ayarlari
```

## Kurulum

### Linux / macOS (manuel)

```bash
pip install -r requirements.txt
pip install -e .
```

### macOS (otomatik - tavsiye edilen)

**Onkosul**: Mac'te Python 3.9+ yuklu olmali. Yoksa Terminal'de:

```bash
# Homebrew yuklu degilse once:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Sonra Python:
brew install python
```

**Calistirma**: Depoyu indirin, Terminal'de proje klasorune girin:

```bash
cd glass_cutting_optimization

# Scriptlere calistirma izni ver (tek seferlik)
chmod +x setup.sh run.sh run_tests.sh quick_start.sh

# Tek komutla her sey: kurulum + calistirma
./quick_start.sh
```

Veya adim adim:

```bash
./setup.sh        # Sanal ortam + bagimliliklar (ilk seferlik)
./run.sh          # Ornek girdiyle optimizasyon
./run_tests.sh    # Birim testler
```

`run.sh` bitiminde cikti klasoru macOS Finder'da otomatik acilir.

> Not: Mac'te Finder bazen `.sh` dosyalarini cift tiklayinca Terminal'de
> calistirmaz. Bunun icin: dosyaya sag tik -> "Aciliacak Uygulama" ->
> "Terminal" secebilir, ya da pratik olarak Terminal'den `./run.sh`
> diyebilirsiniz.

### Windows (otomatik)

`.bat` dosyalarina cift tiklayin:

```cmd
setup.bat         :: Sanal ortam + bagimliliklar (ilk seferlik)
run.bat           :: Ornek girdiyle optimizasyonu calistir
run_tests.bat     :: Birim testleri calistir
quick_start.bat   :: Tek tikla: ilk seferde setup + run, sonra sadece run
```

`quick_start.bat`'a cift tiklayarak sifirdan kurulum + ilk calistirmayi
yapabilirsiniz. Cikti klasoru bitiminde otomatik Explorer'da acilir.

## Web Arayuzu (Streamlit)

Girdileri tablo halinde girip optimizasyonu calistirabilecek ve
sonuclari (ozet, plaka gorselleri, maliyet, fire, kesim plani) gorebilecek
bir arayuz:

```bash
# macOS / Linux
./run_ui.sh

# Windows
run_ui.bat

# veya manuel
streamlit run streamlit_app.py
```

Arayuz tarayicida `http://localhost:8501` adresinde acilir. Ozellikler:
- Stok plakalari ve parca siparislerini **tablo editorunde** duzenleme
  (satir ekle/sil) ya da **JSON yukleme**.
- Kenar cubugundan strateji, sure, kerf / kenar payi ayari.
- Sonuc sekmeleri: plaka gorselleri, plaka detaylari, kesim plani.
- Metin raporunu ve girdiyi JSON olarak indirme.

## Hizli Baslangic

### Manuel CLI (Linux/macOS/Windows)

```bash
python main.py examples/sample_input.json --output output/ --time-limit 30
```

### macOS / Linux

```bash
./run.sh                                   # examples/sample_input.json
./run.sh my_job.json                       # kendi girdiniz
./run.sh my_job.json output_klasoru 60     # ozel cikti + 60s sure siniri
```

### Windows

```cmd
run.bat                                    :: examples\sample_input.json
run.bat my_job.json                        :: kendi girdiniz
run.bat my_job.json output_klasoru 60      :: ozel cikti + 60s sure siniri
```

### Programatik

```python
from glass_optimizer.data.loaders import load_job_from_json
from glass_optimizer.config.settings import OptimizerSettings
from glass_optimizer.optimization.multi_sheet import MultiSheetOrchestrator
from glass_optimizer.presentation.reporter import print_console_report

job = load_job_from_json("examples/sample_input.json")
result = MultiSheetOrchestrator(OptimizerSettings()).solve(
    job.stock, job.parts, job.kerf
)
print_console_report(result)
```

## Girdi Formati (JSON)

```json
{
  "kerf": { "kerf_mm": 3, "edge_trim_mm": 10, "min_offcut_mm": 200 },
  "stock": [
    {
      "sheet_id": "SERT_LOWE_TEC15_4MM_3302x2134",
      "width_mm": 3302,
      "height_mm": 2134,
      "glass_type": "low_e",
      "thickness_mm": 4.0,
      "material": "SERT_LOWE_TEC15_4MM",
      "quantity": 50,
      "unit_cost": 1200.00
    }
  ],
  "parts": [
    {
      "part_id": "PENCERE-1",
      "width_mm": 748,
      "height_mm": 600,
      "quantity": 4,
      "glass_type": "low_e",
      "thickness_mm": 4.0,
      "material": "SERT_LOWE_TEC15_4MM",
      "allow_rotation": true,
      "grain": "none",
      "priority": 5,
      "customer": "ABC Insaat"
    }
  ]
}
```

### `material` (urun/malzeme kodu)

`glass_type` ve `thickness_mm` ayni olsa bile birbirine donusturulemeyen
urunler (orn. **SERT LOW-E TEC 15** ile **SERT LOW-E EKO PRO** — ikisi de
`low_e` 4mm) ayni plakadan kesilemez. `material` alani bu urunleri ayirir:
verildiginde **parca yalnizca ayni `material` koduna sahip stok plakaya**
yerlestirilir. Bos birakilirsa eslestirme `glass_type|thickness_mm`
uzerinden yapilir (geriye donuk uyumlu).

Bir `material` icin birden fazla plaka boyutu tanimlanabilir; cozucu
en-iyi-uygun ile aralarindan secer.

### Gercek siparis verisinden uretme

`examples/sample_input.json`, `examples/build_sample_from_order.py` ile
gercek bir uretim siparisinden uretilmistir (8 farkli urun, ondalikli
olculer mm'ye yuvarlanir). Kendi tablonuzu islemek icin bu scripti
ornek alabilirsiniz.

## Excel ile Girdi

Atolyelerin yaygin kullandigi siparis tablosu formatindaki Excel (.xlsx)
dosyasi dogrudan okunabilir:

| PLAKA TIPI | PLAKA EBAT | URUN EN | URUN BOY | URUN MIKTARI |
|---|---|---|---|---|
| DUZ CAM 4 MM | 6000X3210 | 383.000 | 578.000 | 246 |
| SERT LOW-E TEC 15 4 MM | 3302X2134 | 748.000 | 599.500 | 300 |

Cozumleyici otomatik olarak:
- **material kodu** uretir (her benzersiz "PLAKA TIPI" ayri urun),
- **glass_type** ve **kalinlik** degerlerini urun adindan cikarir,
- **plaka boyutunu** "6000X3210" gibi metinden ayristirir,
- **ondalikli olculeri** mm'ye yuvarlar (599.500 -> 600, 1.554.000 -> 1554),
- her material icin yeterli stok adedini hesaplar.

Kolon adlari esnek eslestirilir (TR/EN, buyuk/kucuk harf). Ornek dosya:
`examples/siparis_ornek.xlsx`.

**Web arayuzunden:** kenar cubugundaki "Dosyadan Yukle" ile .xlsx secin.

**Programatik:**

```python
from glass_optimizer.data.loaders import load_order_table_from_excel
from glass_optimizer.optimization.multi_sheet import MultiSheetOrchestrator
from glass_optimizer.config.settings import OptimizerSettings

job = load_order_table_from_excel("siparisim.xlsx")
result = MultiSheetOrchestrator(OptimizerSettings()).solve(
    job.stock, job.parts, job.kerf
)
```

## Kirma Masasi Kurallari (Cam Catlamasini Onleme)

Cam, kesildikten sonra **kirma masasinda** skor cizgileri boyunca
koparilarak ayristirilir. Cok kucuk, asiri ince-uzun parcalar veya cok
ince fire seritleri bu asamada temiz kirilmaz, catlar/dagilir. Bunu
onlemek icin `kerf` (KerfSettings) altinda uc kural vardir:

| Parametre | Varsayilan | Anlami |
|---|---|---|
| `min_part_mm` | 50 | Masada guvenle elde edilebilen en kucuk parca kenari; daha kucugu **reddedilir** (dogrulama hatasi) |
| `max_aspect_ratio` | 12.0 | Parca uzun/kisa kenar orani ust siniri; asiri ince-uzun parca kirilirken esner, **reddedilir** |
| `min_break_strip_mm` | 50 | Temiz koparilabilen en ince serit; cozucu bir kesim yaninda bundan ince serit (sliver) **birakmaz** |

İlk ikisi girdi dogrulamasinda kontrol edilir (ihlalde acik hata). Ucuncu
kural guillotine cozucude aktiftir: bir izgara blogun kenarinda
`0 < serit < min_break_strip_mm` olacaksa, cozucu sutun/satir sayisini
azaltarak seridi ya 0 ya da koparilabilir genislige tasir. Her uc kural
da `0` verilerek kapatilabilir.

## Cikti

- `output/report.txt` — Detayli rapor (maliyet, fire, kesim plani)
- `output/sheet_01_*.png` — Her plakanin gorseli (renk kodlu yerlesim)
- Konsol cikti — rich tablolari ile ozet

## Testler

```bash
pytest tests/
```

## Optimizasyon Stratejileri

Paket, tek plaka yerlestirmeyi `SheetSolver` arayuzu uzerinden dort
farkli yaklasimla cozer:

| Strateji | Algoritma | Guillotine? | Hiz | Kullanim |
|---|---|---|---|---|
| `guillotine` | Recursive homojen-blok | **Evet** | ~ms / plaka | **Cam koprusu (varsayilan)** |
| `maxrects` | Best Short Side Fit (Jylanki, 2010) | Hayir | ~ms / plaka | Su jeti / lazer, hizli |
| `cpsat` | OR-Tools NoOverlap2D (tam) | Hayir | s-dk / plaka | Kucuk problem / referans |
| `hybrid` | MaxRects + CP-SAT polish (AddHint) | Hayir | s / plaka | Serbest kesimde en yuksek doluluk |

**Cam kesim koprusu duz (edge-to-edge) kestigi icin varsayilan ve
zorunlu strateji `guillotine`'dir.** Bu cozucu yerlesimi her zaman
guillotine kesilebilir uretir (once boylu boyunca, sonra ara kesimler)
ve her bolgeye once tek olcuden izgara blok koyarak parca cesitliligini
de azaltir. Detayli adim adim anlatim:
[docs/nasil_calisir.md](docs/nasil_calisir.md)

`maxrects` / `hybrid` daha yuksek doluluk verebilir ama yerlesim
guillotine olmayabilir; sadece su jeti / lazer gibi serbest kesim
yontemleri icin uygundur.

Strateji secimi:

```bash
./run.sh examples/sample_input.json output 5             # guillotine (varsayilan)
./run.sh examples/sample_input.json output 5 --strategy maxrects
./run.sh examples/sample_input.json output 60 --strategy cpsat
```

Programatik:

```python
from glass_optimizer.config.settings import OptimizerSettings

settings = OptimizerSettings(
    strategy="guillotine",     # varsayilan; cam koprusu icin zorunlu
    time_limit_s=30.0,
)
```

### Karsilastirmali Olcum

`examples/sample_input.json` (gercek siparis, ~9000 parca) uzerinde:

```
strategy     plaka   util%   time_s
guillotine     704    79.2    ~2.0
maxrects       ~700   ~81     ~2.0
```

`maxrects` birkac puan daha yuksek doluluk verir, fakat guillotine
kesilebilir degildir. Cam kesim koprusu icin `guillotine` gecerli olan
tek secenektir; doluluktaki kucuk fark, gecerli kesim plani icin
katlanilan bedeldir (literaturde tipik fark %2-5).

## Buyuk Siparisler

`examples/sample_input.json` gercek bir uretim siparisini icerir:
**8 farkli urun (material)**, 10 stok tanimi, 34 parca kalemi,
~9000 parca. Guillotine cozucu bunu **~2 saniyede** ~704 plaka uzerinde
%79 verimle planlar (yerlesemeyen parca yok, malzemeler karismaz).

Cok buyuk batch'lerde guillotine zaten saniyeler mertebesindedir;
serbest kesim (su jeti/lazer) icin `--strategy maxrects` da ayni hizda
calisir.

## Sektorel Notlar

- **Kerf**: Tipik cam kesim 2-4 mm. Default 3 mm.
- **Kenar payi**: Plaka kenarinda 5-15 mm guvenlik payi (sicilim ve
  duzgun olmayan kenar). Default 10 mm.
- **Standart jumbo boyutlari**: 3210x2250, 6000x3210 (PLF).
- **Standart bant boyutlari**: 2440x1830, 1830x2440.
- **Rotasyon kisiti**: Low-E, ayna, desenli camlarda yon korunmali.
- **Min. offcut**: 100-300 mm altindaki parcalar genelde stoga
  donmuyor (atik).

## Yol Haritasi

- Tam giyotin kesim kisitlamasi (recursive guillotine decomposition).
- Stok offcut'larini yeniden envantere ekleyen kapali dongu.
- Web arayuzu (FastAPI + React).
- Birden fazla kalinlik icin paralel cozum.
