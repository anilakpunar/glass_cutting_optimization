# Cam Kesim Optimizasyon Sistemi

Endustriyel cam kesim operasyonlari icin Google OR-Tools (CP-SAT)
tabanli, katmanli mimaride bir Python uygulamasi.

> **Yeni baslayanlar icin:** Optimizasyonun nasil calistigini basit bir
> ornek uzerinden adim adim ve gorsel olarak anlatan dokuman:
> [docs/nasil_calisir.md](docs/nasil_calisir.md)

## Ozellikler

- **CP-SAT 2D yerlestirme**: NoOverlap2D ile matematiksel olarak gecerli
  cozumler; oncelik agirlikli amac fonksiyonu.
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
- **Gorsel cikti**: Her plaka icin matplotlib PNG'si (renk kodlu).
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
      "sheet_id": "JUMBO-4mm",
      "width_mm": 3210,
      "height_mm": 2250,
      "glass_type": "float",
      "thickness_mm": 4.0,
      "quantity": 3,
      "unit_cost": 850.00
    }
  ],
  "parts": [
    {
      "part_id": "PENCERE-1",
      "width_mm": 900,
      "height_mm": 1500,
      "quantity": 4,
      "allow_rotation": true,
      "grain": "none",
      "priority": 5,
      "customer": "ABC Insaat"
    }
  ]
}
```

## Cikti

- `output/report.txt` — Detayli rapor (maliyet, fire, kesim plani)
- `output/sheet_01_*.png` — Her plakanin gorseli (renk kodlu yerlesim)
- Konsol cikti — rich tablolari ile ozet

## Testler

```bash
pytest tests/
```

## Optimizasyon Stratejileri

Paket, tek plaka yerlestirmeyi `SheetSolver` arayuzu uzerinden uc
farkli yaklasimla cozer:

| Strateji | Algoritma | Hiz | Verim | Kullanim |
|---|---|---|---|---|
| `maxrects` | Best Short Side Fit (Jylanki, 2010) | ~ms / plaka | %85-92 | Binlerce parca, hizli ihtiyac |
| `cpsat` | OR-Tools NoOverlap2D (tam) | s-dk / plaka | Kucuk problemlerde optimal | Az parca, referans |
| `hybrid` | MaxRects + CP-SAT polish (warm-start AddHint) | s / plaka | **En iyi** | **Varsayilan** |

`hybrid` cozucu MaxRects ile milisaniyede bir baslangic cozumu uretir,
ardindan CP-SAT'e `AddHint` ile besler; CP-SAT bu noktadan iyilestirmeye
basladigi icin ayni surede saf CP-SAT'ten cok daha yuksek verim alir.

Strateji secimi:

```bash
./run.sh examples/sample_input.json output 30 --strategy hybrid     # default
./run.sh examples/sample_input.json output 0  --strategy maxrects   # en hizli
./run.sh examples/sample_input.json output 60 --strategy cpsat      # referans
```

Programatik:

```python
from glass_optimizer.config.settings import OptimizerSettings

settings = OptimizerSettings(
    strategy="hybrid",
    time_limit_s=30.0,
    cpsat_polish_time_s=8.0,   # MaxRects sonrasi polish suresi
    max_parts_per_sheet=120,   # CP-SAT modeline gidecek maks parca
)
```

### Karsilastirmali Olcum

`examples/sample_input.json` ile 1 duz + 1 Low-E plaka uzerinde:

```
strategy   placed   util%   time_s   status
maxrects       89    86.1     0.0    MAXRECTS
cpsat          76    76.1    40.0    FEASIBLE
hybrid         90    87.8    16.0    HYBRID-FEASIBLE
```

Tam olcek (~4700 parca, ~208 plaka) tahmini:
- `maxrects`: ~5 saniye toplam
- `hybrid`  : ~30 dakika (polish suresine bagli)
- `cpsat`  : zamansiz, kapasite kaldirilirsa saatler

## Buyuk Siparisler

`examples/sample_input.json` sektorel olcekli ornek icerir:

- Duz cam 4mm 6000x3210 panel: 1628 parca, ~15 plaka
- Sert Low-E TEC 15 4mm 3302x2134 panel: 3091 parca, ~193 plaka

Cok buyuk batch'ler icin `--strategy maxrects` ile saniyeler icinde
bir baslangic plani uretebilir, sonra hibrit ile kalite iyilestirebilirsiniz.

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
