import sys
import time
from pathlib import Path
import subprocess
import etl_parquet


def main():
    start = time.perf_counter()

    project_dir = Path(__file__).resolve().parent
    api_parquet_path = project_dir / "api_parquet.py"

    print("=== [PARQUET] KROK 1: Pobieram dane z GUS (api_parquet.py) ===")
    subprocess.run([sys.executable, str(api_parquet_path)], check=True)

    print("=== [PARQUET] KROK 2: Ładuję pliki Parquet do bazy (etl_parquet.py) ===")
    etl_parquet.main()

    elapsed = time.perf_counter() - start
    print(f" [PARQUET] Cały pipeline (API + ETL) zakończony w {elapsed:.2f} sekundy.")
    print(" [PARQUET] Dane zaktualizowane w bazie 'biblioteki' (fact_biblioteki).")


if __name__ == "__main__":
    main()
