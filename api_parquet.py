import requests
import pandas as pd
from pathlib import Path
from requests.exceptions import RequestException
from tqdm.auto import tqdm
import configparser

TEST_MODE = False
MAX_PAGES = 3

URL = "https://bdl.stat.gov.pl/api/v1"

CONFIG_PATH = Path(__file__).with_name("config.ini")

config = configparser.ConfigParser()
read_files = config.read(CONFIG_PATH, encoding="utf-8")

if not read_files:
    raise RuntimeError(f"Nie znaleziono pliku konfiguracyjnego: {CONFIG_PATH}")

DATA_DIR = Path(config["paths"]["data_dir"])

CLIENT_ID = config.get("api", "client_id")

if not CLIENT_ID:
    raise RuntimeError("Brak api.client_id w config.ini (sekcja [api], klucz client_id).")

HEADERS = {
    "X-ClientId": CLIENT_ID,
    "Accept": "application/json"
}


def safe_get(url, params, headers, retries=3, timeout=30):

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except RequestException as e:
            print(f"⚠️ Problem z zapytaniem (próba {attempt}/{retries}): {e}")
            if attempt == retries:
                print("❌ Maksymalna liczba prób wyczerpana – przerywam pobieranie tej zmiennej.")
                return None


def get_variable_by_city_to_parquet(variable_id, filename_parquet: str):

    url = f"{URL}/data/by-variable/{variable_id}"
    params = {
        "unit-level": 6,
        "format": "json",
        "year": "1999-",
        "page-size": 100
    }

    records = []
    current_url = url
    current_params = params
    page = 0

    print(f"📊 {filename_parquet} — pobieranie danych...")


    with tqdm(desc=f"   {filename_parquet}", unit="strona", leave=False) as pbar:
        while current_url:
            page += 1

            resp = safe_get(current_url, current_params, HEADERS)
            if resp is None:
                break

            data = resp.json()

            results = data.get("results", [])
            for entry in results:
                unit_id = entry["id"]
                unit_name = entry["name"]
                for val in entry.get("values", []):
                    records.append({
                        "unit_id": unit_id,
                        "unit_name": unit_name,
                        "year": val["year"],
                        "value": val["val"]
                    })


            pbar.update(1)


            current_url = data.get("links", {}).get("next")
            current_params = None

            if TEST_MODE and page >= MAX_PAGES:
                print(f" Zatrzymano po {MAX_PAGES} stronach (tryb testowy).")
                break

    df = pd.DataFrame(records)

    out_path = DATA_DIR / filename_parquet
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)

    print(f"💾 Zapisano {len(df)} rekordów do pliku {out_path}\n")


def add_teryt_to_populacja_parquet():

    path = DATA_DIR / "populacja.parquet"
    print(f"🧩 Dodaję kolumnę TERYT do {path}...")

    df = pd.read_parquet(path)
    df["unit_id"] = df["unit_id"].astype(str)

    df["teryt"] = (
        df["unit_id"].str.slice(2, 4) +
        df["unit_id"].str.slice(7, 9) +
        df["unit_id"].str.slice(9, 12)
    )

    df.to_parquet(path, index=False)
    print("✅ Gotowe — populacja.parquet ma kolumnę TERYT.\n")


def run_bdl_fetch_parquet():

    variables = [
        (35720,  "ksiegozbor.parquet"),
        (35719,  "czytelnicy_by_city.parquet"),
        (35715,  "wypozyczenia_ksiegozbioru_by_city.parquet"),
        (35718,  "biblioteki_i_filie_by_city.parquet"),
        (76809,  "wydatki.parquet"),
        (1645341, "populacja.parquet"),
    ]

    print("🚀 [PARQUET] Rozpoczynam pobieranie danych z API GUS...\n")

    for var_id, filename in variables:
        get_variable_by_city_to_parquet(var_id, filename)

    add_teryt_to_populacja_parquet()
    print("🎯 [PARQUET] Wszystkie dane zostały pobrane i zapisane.")


if __name__ == "__main__":
    run_bdl_fetch_parquet()
