#!/usr/bin/env python3
"""
DS18B20 Temperature Monitor — GitHub Pages edition
===================================================
Llegeix el sensor DS18B20 i puja les dades a GitHub Pages via API.
El dashboard HTML (index.html) llegeix el fitxer data.json del repositori.

Requisits:
  pip3 install requests

Configuració:
  Edita les variables de la secció CONFIG aquí sota.
"""

import os
import glob
import time
import csv
import json
import base64
import logging
from datetime import datetime

import requests  # pip3 install requests

# ── CONFIG ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN      = "ghp_XXXXXXXXXXXXXXXX"   # Personal Access Token (repo scope)
GITHUB_USER       = "el-teu-usuari"          # Nom d'usuari de GitHub
GITHUB_REPO       = "temperature-monitor"   # Nom del repositori
GITHUB_BRANCH     = "gh-pages"              # Branca de GitHub Pages

READ_INTERVAL_SECONDS = 30    # Cada quants segons llegir el sensor
LOG_FILE              = "temperature_log.csv"
MAX_HISTORY           = 200   # Punts que es guarden al data.json
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

history = []   # llista de lectures en memòria


# ── Sensor ────────────────────────────────────────────────────────────────────

def find_sensor():
    devices = glob.glob("/sys/bus/w1/devices/28-*/w1_slave")
    if not devices:
        raise FileNotFoundError(
            "Sensor DS18B20 no trobat. Comprova el cablejat i que 1-Wire "
            "estigui activat (dtoverlay=w1-gpio a /boot/config.txt)."
        )
    return devices[0]


def read_temperature(sensor_path):
    with open(sensor_path) as f:
        lines = f.readlines()
    if lines[0].strip()[-3:] != "YES":
        raise ValueError("Error CRC — reintentant.")
    celsius = float(lines[1].split("t=")[-1]) / 1000.0
    return celsius


# ── CSV local ─────────────────────────────────────────────────────────────────

def init_csv():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            csv.writer(f).writerow(["timestamp", "celsius", "fahrenheit"])
        log.info("Creat fitxer de log: %s", LOG_FILE)


def append_csv(ts, celsius, fahrenheit):
    with open(LOG_FILE, "a", newline="") as f:
        csv.writer(f).writerow([ts, f"{celsius:.3f}", f"{fahrenheit:.3f}"])


# ── GitHub API ────────────────────────────────────────────────────────────────

BASE_URL = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def get_file_sha(path):
    """Retorna el SHA del fitxer al repo (necessari per actualitzar-lo)."""
    url = f"{BASE_URL}/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{path}"
    r = requests.get(url, headers=HEADERS, params={"ref": GITHUB_BRANCH})
    if r.status_code == 200:
        return r.json()["sha"]
    return None  # El fitxer encara no existeix


def push_file(path, content_str, commit_message):
    """Crea o actualitza un fitxer al repositori."""
    url = f"{BASE_URL}/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{path}"
    sha = get_file_sha(path)
    payload = {
        "message": commit_message,
        "content": base64.b64encode(content_str.encode()).decode(),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=HEADERS, json=payload)
    if r.status_code in (200, 201):
        log.info("✓ %s pujat a GitHub Pages", path)
    else:
        log.error("Error pujant %s: %s %s", path, r.status_code, r.text)


def push_data_json():
    """Puja data.json amb les últimes lectures."""
    payload = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "history": history[-MAX_HISTORY:],
    }
    push_file(
        "data.json",
        json.dumps(payload, indent=2),
        f"sensor: update {payload['updated']}",
    )


def push_csv_log():
    """Puja el fitxer CSV complet (cada 10 lectures)."""
    if not os.path.exists(LOG_FILE):
        return
    with open(LOG_FILE) as f:
        content = f.read()
    push_file(LOG_FILE, content, "sensor: update csv log")


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    init_csv()

    # Espera fins que el sensor estigui disponible
    sensor_path = None
    while sensor_path is None:
        try:
            sensor_path = find_sensor()
            log.info("Sensor trobat: %s", sensor_path)
        except FileNotFoundError as e:
            log.error("%s — reintentant en 10 s", e)
            time.sleep(10)

    log.info("Iniciant lectures cada %d s → GitHub Pages", READ_INTERVAL_SECONDS)
    reading_count = 0

    while True:
        try:
            celsius = read_temperature(sensor_path)
            fahrenheit = celsius * 9 / 5 + 32
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            reading = {
                "time": now,
                "celsius": round(celsius, 3),
                "fahrenheit": round(fahrenheit, 3),
            }
            history.append(reading)
            if len(history) > MAX_HISTORY:
                history.pop(0)

            append_csv(now, celsius, fahrenheit)
            log.info("🌡  %.3f °C  |  %.3f °F", celsius, fahrenheit)

            # Puja data.json a cada lectura
            push_data_json()

            # Puja el CSV cada 10 lectures
            reading_count += 1
            if reading_count % 10 == 0:
                push_csv_log()

        except Exception as e:
            log.warning("Error: %s", e)

        time.sleep(READ_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
