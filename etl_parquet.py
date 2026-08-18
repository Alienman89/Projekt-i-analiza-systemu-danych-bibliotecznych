import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
import csv
import configparser
import pandas as pd


CONFIG_PATH = Path(__file__).with_name("config.ini")

config = configparser.ConfigParser()
read_files = config.read(CONFIG_PATH, encoding="utf-8")

if not read_files:
    raise RuntimeError(f"Nie znaleziono pliku konfiguracyjnego: {CONFIG_PATH}")

DB_CONFIG = {
    "host": config["database"]["host"],
    "port": config.getint("database", "port"),
    "dbname": config["database"]["dbname"],
    "user": config["database"]["user"],
    "password": config["database"]["password"],
}

DATA_DIR = Path(config["paths"]["data_dir"])
TERC_FILENAME = config["paths"]["terc_filename"]


MEASURE_FILES = [
    ("populacja.parquet", "populacja", True),
    ("czytelnicy_by_city.parquet", "czytelnicy", False),
    ("wypozyczenia_ksiegozbioru_by_city.parquet", "wypozyczenia", False),
    ("biblioteki_i_filie_by_city.parquet", "placowki", False),
    ("ksiegozbor.parquet", "ksiegozbior", False),
    ("wydatki.parquet", "wydatki", False),
]


def get_conn():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception:
        print(" Blad przy probie polaczenia z baza danych.")
        raise


def init_schema(conn):

    create_sql = """
    CREATE TABLE IF NOT EXISTS stg_teryt (
      teryt  CHAR(7)   PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS dim_year (
      year SMALLINT PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS fact_biblioteki (
      teryt  CHAR(7)   NOT NULL,
      year   SMALLINT  NOT NULL,
      populacja            NUMERIC(18,2),
      czytelnicy           BIGINT,
      wypozyczenia         BIGINT,
      ksiegozbior          BIGINT,
      biblioteki_i_filie   INTEGER,
      wydatki              NUMERIC(18,2),

      CONSTRAINT pk_fact PRIMARY KEY (teryt, year),
      CONSTRAINT fk_fact_teryt FOREIGN KEY (teryt) REFERENCES stg_teryt(teryt),
      CONSTRAINT fk_fact_year  FOREIGN KEY (year)  REFERENCES dim_year(year)
    );

    CREATE INDEX IF NOT EXISTS ix_fact_year  ON fact_biblioteki (year);
    CREATE INDEX IF NOT EXISTS ix_fact_teryt ON fact_biblioteki (teryt);

    CREATE TABLE IF NOT EXISTS stg_miary (
      unit_id   text,
      unit_name text,
      year      smallint,
      value     text,
      teryt     text,
      source    text
    );

    CREATE TABLE IF NOT EXISTS map_unitid_teryt (
      unit_id text PRIMARY KEY,
      teryt   text
    );
    """

    with conn.cursor() as cur:
        cur.execute(create_sql)
    conn.commit()


def clear_staging(conn):

    with conn.cursor() as cur:
        cur.execute("TRUNCATE stg_miary;")
    conn.commit()


def load_measures_parquet_to_stg(conn):

    for filename, source, has_teryt in MEASURE_FILES:
        path = DATA_DIR / filename
        print(f"Laduje {path} jako source='{source}'...")

        if not path.exists():
            print(f" Plik {path} nie istnieje - pomijam zrodlo '{source}'.")
            continue

        df = pd.read_parquet(path)
        rows = []

        for index, row in df.iterrows():
            unit_id = str(row["unit_id"])
            unit_name = str(row["unit_name"])
            year = int(row["year"])
            value = str(row["value"])

            teryt = None
            if has_teryt and "teryt" in df.columns and not pd.isna(row["teryt"]):
                teryt = str(row["teryt"])

            rows.append((unit_id, unit_name, year, value, teryt, source))

        if not rows:
            print(f" Brak danych w {path} - pomijam.")
            continue

        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO stg_miary (unit_id, unit_name, year, value, teryt, source)
                VALUES %s
                """,
                rows,
            )



def build_map_unitid_teryt_and_fill(conn):

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO map_unitid_teryt (unit_id, teryt)
            SELECT DISTINCT unit_id, teryt
            FROM stg_miary
            WHERE source = 'populacja'
              AND teryt IS NOT NULL AND teryt <> ''
            ON CONFLICT (unit_id) DO NOTHING;
        """
        )

        cur.execute(
            """
            UPDATE stg_miary m
            SET teryt = d.teryt
            FROM map_unitid_teryt d
            WHERE m.teryt IS NULL
              AND m.unit_id = d.unit_id;
        """
        )
    conn.commit()


def fill_dim_year(conn):

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dim_year (year)
            SELECT DISTINCT year
            FROM stg_miary
            ORDER BY year
            ON CONFLICT (year) DO NOTHING;
        """
        )
    conn.commit()


def load_terc_and_fill_stg_teryt(conn):

    path = DATA_DIR / TERC_FILENAME
    print(f"Laduje TERC z {path}...")

    terc_rows = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            terc_rows.append(r)

    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT teryt FROM stg_miary WHERE teryt IS NOT NULL;")
        teryt_needed = {row[0] for row in cur.fetchall()}

    def build_teryt(row):
        woj = row.get("WOJ")
        pow_ = row.get("POW")
        gmi = row.get("GMI")
        rodz = row.get("RODZ")

        if not woj or not rodz:
            return None
        try:
            woj_val = int(float(woj))
            rodz_val = int(float(rodz))
        except ValueError:
            return None

        pow_val = int(float(pow_)) if pow_ not in (None, "", "NaN") else 0
        gmi_val = int(float(gmi)) if gmi not in (None, "", "NaN") else 0

        return f"{woj_val:02d}{pow_val:02d}{gmi_val:02d}{rodz_val:1d}"

    unique_teryt = set()

    for r in terc_rows:
        teryt = build_teryt(r)
        if not teryt or teryt not in teryt_needed:
            continue
        unique_teryt.add(teryt)

    rows = [(t,) for t in unique_teryt]

    if rows:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO stg_teryt (teryt)
                VALUES %s
                ON CONFLICT (teryt) DO NOTHING;
                """,
                rows,
            )
        conn.commit()


def build_fact_biblioteki(conn):
    sql = """
    INSERT INTO fact_biblioteki (
      teryt, year,
      populacja,
      czytelnicy,
      wypozyczenia,
      ksiegozbior,
      biblioteki_i_filie,
      wydatki
    )
    SELECT
      m.teryt,
      m.year::smallint,
      MAX(CASE WHEN m.source='populacja'
               THEN REPLACE(m.value, ',', '.')::numeric(18,2) END)              AS populacja,
      MAX(CASE WHEN m.source='czytelnicy'
               THEN REGEXP_REPLACE(m.value, '[^0-9]', '', 'g')::numeric END)   AS czytelnicy,
      MAX(CASE WHEN m.source='wypozyczenia'
               THEN REGEXP_REPLACE(m.value, '[^0-9]', '', 'g')::numeric END)   AS wypozyczenia,
      MAX(CASE WHEN m.source='ksiegozbior'
               THEN REGEXP_REPLACE(m.value, '[^0-9]', '', 'g')::numeric END)   AS ksiegozbior,
      MAX(CASE WHEN m.source='placowki'
               THEN REGEXP_REPLACE(m.value, '[^0-9]', '', 'g')::int END)       AS biblioteki_i_filie,
      MAX(CASE WHEN m.source='wydatki'
               THEN REPLACE(m.value, ',', '.')::numeric(18,2) END)             AS wydatki
    FROM stg_miary m
    JOIN stg_teryt t ON t.teryt = m.teryt
    WHERE m.teryt IS NOT NULL AND m.teryt <> ''
    GROUP BY m.teryt, m.year
    ON CONFLICT (teryt, year) DO UPDATE SET
      populacja = EXCLUDED.populacja,
      czytelnicy = EXCLUDED.czytelnicy,
      wypozyczenia = EXCLUDED.wypozyczenia,
      ksiegozbior = EXCLUDED.ksiegozbior,
      biblioteki_i_filie = EXCLUDED.biblioteki_i_filie,
      wydatki = EXCLUDED.wydatki;
    """
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def main():
    conn = get_conn()
    try:
        conn.autocommit = False

        print("-> [PARQUET] Tworze strukture bazy (tabele dim_*, fact_*, stg_*)...")
        init_schema(conn)

        print("-> [PARQUET] Czyszcze staging...")
        clear_staging(conn)

        print("-> [PARQUET] Laduje miary z plikow Parquet do stg_miary...")
        load_measures_parquet_to_stg(conn)

        print("-> [PARQUET] Buduje mape unit_id -> teryt i uzupelniam teryt w stg_miary...")
        build_map_unitid_teryt_and_fill(conn)

        print("-> [PARQUET] Uzupelniam dim_year...")
        fill_dim_year(conn)

        print("-> [PARQUET] Uzupelniam stg_teryt na podstawie TERC...")
        load_terc_and_fill_stg_teryt(conn)

        print("-> [PARQUET] Buduje fact_biblioteki...")
        build_fact_biblioteki(conn)

        conn.commit()
        print("✔ [PARQUET] Gotowe. Dane sa w fact_biblioteki (commit).")
    except Exception:
        conn.rollback()
        print(" [PARQUET] Wystapil blad podczas ETL - wykonano ROLLBACK wszystkich zmian.")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()


