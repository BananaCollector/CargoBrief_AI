# CargoBrief AI

CargoBrief AI to aplikacja full-stack wspierająca pracowników w zamienianiu wiadomości klientów w uporządkowane zlecenia transportowe. System może analizować treść wiadomości i zaproponować dopasowanie pojazdu, ale to pracownik sprawdza i zatwierdza każde zlecenie.

## Funkcje

- Tworzenie, przeglądanie, edycja i usuwanie zleceń transportowych.
- Kolejka pracownika z wyszukiwaniem, filtrowaniem, edycją danych i zatwierdzaniem zleceń.
- Analiza wiadomości przez Google Gemini: ekstrakcja danych przesyłki, adresów i dostępnych danych kontaktowych. Brakujące informacje nie są zgadywane.
- Deterministyczne dopasowanie pojazdu na podstawie wymiarów i ładowności; dopasowanie nie jest wykonywane przez AI.
- Planowanie wysyłek i grupowanie zgodnych zleceń, z opcjonalnymi propozycjami AI.
- Opcjonalna obsługa skrzynki Gmail przez IMAP/SMTP: odbiór wiadomości, filtr tematu, analiza oraz powiadomienia o terminie wysyłki.
- Widok developerski ze stanem backendu i bazy danych.

## Technologie

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, React Router, Lucide.
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic.
- **Baza danych:** SQLite.
- **AI:** Google Gemini API (opcjonalnie).
- **Testy:** Pytest (backend).

Frontend i backend znajdują się w osobnych katalogach. Logika biznesowa i integracje zewnętrzne są realizowane po stronie backendu. Dane otrzymane od AI są walidowane przed użyciem, a decyzje wymagające zatwierdzenia pozostają po stronie pracownika.

## Wymagania

- Python 3.11 lub nowszy.
- Node.js i npm.
- Klucz Gemini jest opcjonalny. Integracja poczty wymaga konta Gmail z włączonym IMAP oraz hasła aplikacji Google.

## Uruchomienie lokalne

### 1. Backend

W pierwszym terminalu, z katalogu głównego repozytorium:

```bash
cd backend
python -m venv .venv
```

Aktywuj środowisko wirtualne:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Zainstaluj zależności, skopiuj przykładową konfigurację i zastosuj migracje:

```bash
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
```

W systemie Windows skopiuj `.env.example` do `.env` za pomocą Eksploratora plików lub polecenia `Copy-Item .env.example .env` w PowerShell.

Uruchom API:

```bash
uvicorn app.main:app --reload
```

Backend działa domyślnie pod adresem `http://127.0.0.1:8000`. Interaktywna dokumentacja API FastAPI (Swagger UI) jest dostępna pod `http://127.0.0.1:8000/docs`, a schemat OpenAPI pod `http://127.0.0.1:8000/openapi.json`.

### 2. Frontend

W drugim terminalu, z katalogu głównego repozytorium:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend działa domyślnie pod adresem `http://localhost:5173`. Zmienna `VITE_API_URL` w `frontend/.env` wskazuje adres backendu i domyślnie ma wartość `http://localhost:8000`.

### 3. Konfiguracja opcjonalnych integracji

Ustawienia backendu znajdują się w `backend/.env`. Wartości przykładowe można zmienić zgodnie z potrzebami:

- `GEMINI_API_KEY` — klucz API włączający analizę przez Gemini i propozycje grupowania wysyłek oparte na Gemini. Bez klucza interaktywna analiza wiadomości i propozycje grupowania działają w trybie demonstracyjnym. Automatyczna analiza wiadomości odebranych przez Gmail wymaga klucza; bez niego wiadomości pozostają oczekujące na analizę.
- `GEMINI_MODEL` — model Gemini; domyślna wartość znajduje się w `backend/.env.example`.
- `GMAIL_ADDRESS` i `GMAIL_APP_PASSWORD` — adres skrzynki Gmail i jej hasło aplikacji.
- `EMAIL_POLL_INTERVAL_SECONDS` — odstęp między automatycznymi próbami sprawdzenia poczty.
- `DEV_TOOLS_ENABLED` — domyślnie `false`; włącza możliwość czyszczenia danych w widoku developerskim. Używaj wyłącznie lokalnie.

Nie umieszczaj kluczy API ani haseł w repozytorium. Do Gmaila należy użyć hasła aplikacji, a nie hasła do konta. Podstawowe operacje CRUD i deterministyczne dopasowanie pojazdu działają bez konfiguracji Gemini. Integracja Gmail uruchamia się tylko po skonfigurowaniu adresu i hasła.

## Testy i build

Testy backendu:

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
```

Build frontendu:

```bash
cd frontend
npm run build
```

## Wsparcie narzędzi AI

Podczas pracy nad projektem korzystałem z GitHub Copilot jako wsparcia przy implementacji, analizie kodu i przygotowywaniu testów. Wygenerowane sugestie były weryfikowane i dostosowywane do wymagań projektu.
