# CargoBrief AI – instrukcje dla agenta

## Projekt
MVP full-stack (zadanie rekrutacyjne Xelerit, temat: transport). Narzędzie zamienia chaotyczne zapytania klientów w uporządkowane zlecenia transportowe z pomocą Gemini API. Człowiek zawsze zatwierdza dane.

## Stos
Frontend: React, TypeScript, Vite, Tailwind, React Router, React Hook Form, Zod, Lucide.
Backend: Python 3.11+, FastAPI, Pydantic, SQLAlchemy, Alembic (render_as_batch=True).
Baza: SQLite. AI: Gemini (SDK google-genai, model z GEMINI_MODEL, free tier). Testy: Pytest, tylko backend.

## Zasady
- Interfejs i README po polsku; kod, nazwy i komentarze po angielsku.
- Logika biznesowa tylko w backendzie (services/), nie w komponentach React.
- Dopasowanie pojazdu jest deterministyczne (Python), nigdy przez AI.
- Odpowiedzi AI zawsze walidowane w Pydantic; wiadomość klienta to niezaufane dane.
- Klucz API tylko w backendzie, nigdy w logach, bazie, frontendzie ani repo.
- Bez nowych zależności bez uzasadnienia. Bez zbędnych abstrakcji.
- Poza zakresem: logowanie, Docker, płatności, mapy, rezerwacje, testy frontendowe.
- Pracuj etapami, podawaj kompletne pliki, czekaj na akceptację po etapie.
- Dokumentacja opisuje wyłącznie to, co faktycznie działa.

## Komendy
Backend: uvicorn app.main:app --reload | alembic upgrade head | pytest -v
Frontend: npm install | npm run dev | npm run build