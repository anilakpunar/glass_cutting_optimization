# Cam Kesim Optimizasyon Sistemi

Endustriyel cam kesim operasyonlari icin Google OR-Tools (CP-SAT)
tabanli, katmanli mimaride bir Python uygulamasi.

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

## Buyuk Siparisler & Performans

CP-SAT 2D yerlestirme tek bir plakada en fazla ~100-150 parca ornegi
ile makul surede cozulur. Bu paket binlerce parcali siparisleri
**sira li plaka cozumu** ile ele alir; her plakaya en fazla
`max_parts_per_sheet` (default 120) aday verilir.

`examples/sample_input.json` sektorel olcekli ornek icerir:

- Duz cam 4mm 6000x3210 panel: 1628 parca, ~15 plaka
- Sert Low-E TEC 15 4mm 3302x2134 panel: 3091 parca, ~193 plaka

Toplam ~70 dakika beklenir (default 30 s/plaka). Hizlandirmak icin:

```bash
./run.sh examples/sample_input.json output 10   # plaka basina 10 s
```

Cozucu parametrelerini ozellestirmek icin `OptimizerSettings` icindeki
`max_parts_per_sheet` (default 120) ve `candidate_area_factor` (default
1.3) degerleri programatik kullanimda ayarlanabilir.

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
