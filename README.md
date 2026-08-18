# Projekt i analiza systemu danych bibliotecznych na podstawie danych GUS z lat 1999–2024 z wykorzystaniem SQL, Pythona i Power BI

**Praca Dyplomowa Inżynierska**  
**Autor:** Dawid Buca  
**Uczelnia:** Akademia WIT w Warszawie (Wydział Technologii Informatycznych i Zarządzania)  
**Kierunek:** Informatyczne Techniki Zarządzania  
**Promotor:** Mgr inż. Maria Ocet  
**Rok akademicki:** 2025/2026  

---

## 📄 Pełna Dokumentacja Pracy

Pełny tekst pracy inżynierskiej w formacie PDF znajduje się w repozytorium:  
👉 **[Pobierz/Zobacz Treść Pracy (PDF)]([./documents/praca_inż.pdf])**

---

## 📌 O Projekcie

System przeznaczony jest do automatycznego pozyskiwania, przetwarzania oraz analizy danych statystycznych opisujących działalność bibliotek publicznych w Polsce na poziomie gmin. Wykorzystuje oficjalne dane pochodzące z **Banku Danych Lokalnych (BDL) Głównego Urzędu Statystycznego (GUS)** z lat 1999–2024.

Głównym celem inżynierskim było zbudowanie zautomatyzowanego potoku danych (ETL) w języku Python, zasilającego relacyjną hurtownię danych PostgreSQL, oraz stworzenie interaktywnego środowiska analityczno-predykcyjnego w Power BI.

### Kluczowe Funkcjonalności:
- **Automatyczny ETL:** Ekstrakcja danych z REST API GUS BDL ze stronicowaniem, obsługą błędów połączeń oraz odpornością na pętle paginacji.
- **Format Parquet:** Zastosowanie kolumnowego formatu pośredniego Parquet wykazującego wyższą wydajność przetwarzania w porównaniu do klasycznego CSV.
- **Model Danych Kimballa:** Projekt relacyjnej hurtowni w PostgreSQL opartej na tabeli faktów (`fact_biblioteki`), wymiarze czasu (`dim_year`) oraz technicznych tabelach wspierających mapowanie kodów TERYT.
- **Spójność i Transakcyjność:** Przetwarzanie w ramach transakcji bazy danych z obsługą operacji `UPSERT` (`ON CONFLICT`) chroniącą przed duplikacją rekordów.
- **Raport Analityczny Power BI:** Zestawienie wskaźników bezwzględnych oraz względnych (np. czytelnicy na 1 tys. mieszkańców, wypożyczenia per capita) na tle średnich wojewódzkich i krajowych.
- **Moduł Predykcyjny (Python + Scikit-Learn):** Wbudowany model regresji liniowej prognozujący trendy czytelnictwa do roku 2030 w rozbiciu na typy gmin (miejskie, miejsko-wiejskie, wiejskie) z wyznaczonym błędem RMSE = 6,58.

---

## 🏗 Architektura Systemu

Architektura logiczna składa się z 4 głównych warstw:
1. **Warstwa Pozyskiwania (Extract):** Pobieranie surowych danych z API GUS BDL (poziom `unit_level=6`).
2. **Warstwa Przetwarzania (Transform):** Mapowanie identyfikatorów jednostek na kody TERYT, czyszczenie typów danych i agregacja do formatu Parquet.
3. **Warstwa Składowania (Load):** Ładowanie do hurtowni PostgreSQL w schemacie gwiazdy.
4. **Warstwa Analityczno-Prezentacyjna:** Model DAX i interaktywny dashboard w Power BI.

Przepływ danych: **API GUS BDL ➔ Pliki Parquet ➔ Baza PostgreSQL ➔ Power BI**.

---

## 🛠 Technologie i Narzędzia

- **Język programowania:** Python 3.x
- **Biblioteki Python:** `pandas`, `numpy`, `requests`, `scikit-learn`, `psycopg2`, `tqdm`, `pyarrow`
- **Baza danych:** PostgreSQL
- **Analityka i Wizualizacja:** Power BI Desktop (DAX, Power Query)
- **Źródła danych:** API Banku Danych Lokalnych GUS, Rejestr TERC TERYT

---

## 📁 Struktura Repozytorium

- **docs/praca_inż.pdf** - Pełna treść pracy dyplomowej inżynierskiej
- **docs/Instrukcja_uruchomienia.pdf** - Instrukcja wdrożenia i uruchomienia projektu
- **main_parquet.py** - Moduł sterujący / orkiestrator pipeline'u ETL
- **api_parquet.py** - Moduł ekstrakcji danych z API GUS BDL
- **etl_parquet.py** - Moduł transformacji i ładowania danych do PostgreSQL
- **config.ini** - Plik konfiguracyjny (baza danych, ścieżki)
- **raport.pbix** - Plik raportu analitycznego Power BI
- **requirements.txt** - Zależności bibliotek Pythona
- **README.md** - Opis projektu

---

## 📊 Wybrane Wyniki i Badania

1. **Walidacja danych (Spot-check & Null Check):** Zweryfikowana 100% zgodność wartości tabeli faktów z bazą BDL GUS dla losowych jednostek (np. Gmina Kłodzko TERYT: `0208021`).
2. **Optymalizacja wyjścia:** Zastosowanie plików Parquet pozwoliło odczuwalnie skrócić całkowity czas przetwarzania wsadowego w porównaniu do tradycyjnych plików CSV.
3. **Model Prognostyczny:** Estymacja liniowa dla czytelnictwa per capita wyznaczyła ogólnokrajowy trend spadkowy z dopasowaniem o błędzie RMSE = 6,58 czytelnika / 1 tys. mieszkańców.

---

## 📝 Autor i Licencja

- **Autor:** Dawid Buca
- **Kontakt:** Profil GitHub (`Alienman89`)
- **Licencja:** Projekt wykonany w celach naukowo-dydaktycznych w ramach pracy inżynierskiej na uczelni Akademia WIT.
