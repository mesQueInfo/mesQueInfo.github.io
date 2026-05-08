# DS18B20 Temperature Monitor — GitHub Pages

El Raspberry Pi llegeix el sensor i puja `data.json` al repositori.
GitHub Pages serveix el dashboard HTML que llegeix aquell JSON automàticament.

---

## Arquitectura

```
Raspberry Pi                   GitHub
─────────────────────          ──────────────────────────────────
DS18B20 sensor                 Repositori (branca gh-pages)
    ↓                              ├── index.html   ← dashboard
ds18b20_github.py                  ├── data.json    ← dades del sensor
    ↓  (GitHub API cada 30s)       └── temperature_log.csv
    └──────────────────────────────→
                                       ↑
                               GitHub Pages (HTTPS públic)
                               https://usuari.github.io/repo/
```

---

## 1. Crea el repositori a GitHub

1. Crea un repositori nou (p.ex. `temperature-monitor`)
2. Activa **GitHub Pages**: Settings → Pages → Branch: `gh-pages` / root
3. Puja `index.html` a la branca `gh-pages`:

```bash
git clone https://github.com/el-teu-usuari/temperature-monitor
cd temperature-monitor
git checkout --orphan gh-pages
git rm -rf .
cp /path/to/index.html .
git add index.html
git commit -m "init dashboard"
git push origin gh-pages
```

---

## 2. Crea un Personal Access Token (PAT)

GitHub → Settings → Developer settings → Personal access tokens → scope: **repo**

---

## 3. Configura el script

Edita les variables al principi de `ds18b20_github.py`:

```python
GITHUB_TOKEN  = "ghp_XXXXXXXXXXXXXXXX"
GITHUB_USER   = "el-teu-usuari"
GITHUB_REPO   = "temperature-monitor"
GITHUB_BRANCH = "gh-pages"
READ_INTERVAL_SECONDS = 30
```

> **Seguretat**: millor usar variable d'entorn:
> `export GITHUB_TOKEN="ghp_xxx"` i al codi `os.environ["GITHUB_TOKEN"]`

---

## 4. Cablejat DS18B20

```
VCC  (vermell) → 3.3V  (Pin 1)
GND  (negre)   → GND   (Pin 6)
DATA (groc)    → GPIO4 (Pin 7)
⚠️  Resistència pull-up 4.7kΩ entre DATA i VCC
```

---

## 5. Activa 1-Wire i executa

```bash
sudo raspi-config → Interface Options → 1-Wire → Enable → Reboot
ls /sys/bus/w1/devices/   # ha de mostrar 28-xxxxxxxxxxxx

pip3 install requests
python3 ds18b20_github.py
```

---

## 6. Dashboard

```
https://el-teu-usuari.github.io/temperature-monitor/
```

El dashboard es refresca cada **60 segons**.

---

## 7. Execució automàtica en arrencar

```bash
crontab -e
# Afegeix:
@reboot sleep 30 && python3 /home/pi/ds18b20_github.py >> /home/pi/temp.log 2>&1 &
```
