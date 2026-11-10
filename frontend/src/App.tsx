import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, Loader2, ShieldCheck, Truck } from 'lucide-react';
import { Link, Route, Routes } from 'react-router-dom';

type HealthResponse = {
  status: string;
  service: string;
  database: string;
  cors: string;
};

const apiBaseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function App() {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-3 text-lg font-semibold text-slate-900">
            <div className="rounded-xl bg-sky-100 p-2 text-sky-700">
              <Truck className="h-5 w-5" />
            </div>
            CargoBrief AI
          </Link>
          <nav className="hidden gap-6 text-sm font-medium text-slate-600 sm:flex">
            <Link to="/" className="transition hover:text-slate-900">
              Start
            </Link>
            <span className="text-slate-300">|</span>
            <span className="text-slate-500">Nowe zlecenie</span>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
        </Routes>
      </main>
    </div>
  );
}

function HomePage() {
  const [status, setStatus] = useState<'checking' | 'connected' | 'error'>('checking');
  const [message, setMessage] = useState('Sprawdzam połączenie z backendem...');

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/health`, {
          method: 'GET',
          headers: { Accept: 'application/json' },
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const payload = (await response.json()) as HealthResponse;
        setStatus('connected');
        setMessage(`${payload.service} – połączono z ${payload.database}. CORS: ${payload.cors}.`);
      } catch (error) {
        setStatus('error');
        setMessage(
          error instanceof Error
            ? `Nie można połączyć się z backendem (${error.message}).`
            : 'Nie można połączyć się z backendem.',
        );
      }
    };

    checkHealth();
  }, []);

  return (
    <section className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
      <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-5 inline-flex items-center gap-2 rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-sky-700">
          <ShieldCheck className="h-3.5 w-3.5" />
          MVP transportowy
        </div>

        <h1 className="text-4xl font-bold tracking-tight text-slate-900">
          Przetwarzaj maile klientów w gotowe zlecenia transportowe.
        </h1>

        <p className="mt-4 max-w-xl text-base text-slate-600">
          CargoBrief AI zbiera dane z chaosu, sprawdza poprawność informacji i przygotowuje zlecenie do
          zatwierdzenia przez człowieka.
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
          <button className="rounded-xl bg-sky-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-sky-700">
            Utwórz nowe zlecenie
          </button>
          <button className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100">
            Wczytaj przykład
          </button>
        </div>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Status backendu</h2>
          {status === 'connected' ? (
            <span className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Połączono
            </span>
          ) : status === 'error' ? (
            <span className="inline-flex items-center gap-2 rounded-full bg-rose-100 px-2.5 py-1 text-xs font-medium text-rose-700">
              <AlertCircle className="h-3.5 w-3.5" />
              Błąd
            </span>
          ) : (
            <span className="inline-flex items-center gap-2 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Ładowanie
            </span>
          )}
        </div>

        <p className="text-sm text-slate-600">{message}</p>

        <div className="mt-6 rounded-2xl bg-slate-50 p-4">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">Cel produktu</p>
          <p className="mt-2 text-sm text-slate-700">
            Klient wkleja wiadomość, AI rozpoznaje dane, a człowiek akceptuje typ pojazdu i szczegóły zlecenia.
          </p>
        </div>
      </div>
    </section>
  );
}

export default App;
