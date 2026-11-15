import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Loader2,
  RefreshCw,
  Server,
  ShieldAlert,
  Trash2,
  XCircle,
} from 'lucide-react';
import { ApiError, apiBaseUrl, fetchJson } from './api';

type DevDiagnostics = {
  status: 'ok';
  app_name: string;
  app_version: string;
  python_version: string;
  clear_enabled: boolean;
  database: {
    connected: boolean;
    dialect: string;
    location: string;
    current_revision: string | null;
    head_revision: string | null;
    migration_status: 'unknown' | 'not_initialized' | 'up_to_date' | 'pending';
  };
  tables: { name: string; row_count: number | null; exists: boolean; clearable: boolean }[];
  integrations: Record<string, boolean>;
  recent_errors: { timestamp: string; level: string; logger: string }[];
};

const migrationLabels: Record<DevDiagnostics['database']['migration_status'], string> = {
  unknown: 'Nieznany',
  not_initialized: 'Brak tabeli rewizji',
  up_to_date: 'Aktualne',
  pending: 'Wymaga migracji',
};

function DevPage() {
  const [diagnostics, setDiagnostics] = useState<DevDiagnostics | null>(null);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline' | 'error'>('checking');
  const [backendError, setBackendError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isClearingTable, setIsClearingTable] = useState<string | null>(null);
  const [confirmations, setConfirmations] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const recordBackendFailure = useCallback((requestError: unknown) => {
    if (requestError instanceof ApiError) {
      setBackendStatus('error');
      setBackendError(`Backend odpowiedział błędem HTTP ${requestError.status}: ${requestError.message}`);
    } else {
      setBackendStatus('offline');
      setBackendError('Brak połączenia z backendem. Sprawdź, czy serwer działa i czy adres API jest poprawny.');
    }
  }, []);

  const loadDiagnostics = useCallback(async (refresh = false) => {
    setError(null);
    setBackendStatus('checking');
    setBackendError(null);
    if (refresh) setIsRefreshing(true);
    else setIsLoading(true);
    try {
      setDiagnostics(await fetchJson<DevDiagnostics>('/api/v1/dev/status'));
      setBackendStatus('online');
    } catch (requestError) {
      setDiagnostics(null);
      recordBackendFailure(requestError);
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : 'Nie udało się połączyć z backendem.',
      );
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [recordBackendFailure]);

  useEffect(() => {
    void loadDiagnostics();
  }, [loadDiagnostics]);

  const clearTable = async (tableName: string) => {
    if (confirmations[tableName] !== tableName) return;
    if (!window.confirm(`Czy na pewno usunąć wszystkie rekordy z tabeli „${tableName}”?`)) return;

    setIsClearingTable(tableName);
    setError(null);
    setMessage(null);
    try {
      const result = await fetchJson<{ table_name: string; deleted_count: number }>(
        `/api/v1/dev/tables/${encodeURIComponent(tableName)}/clear`,
        {
          method: 'POST',
          body: JSON.stringify({ confirm_table_name: tableName }),
          headers: { 'Content-Type': 'application/json' },
        },
      );
      setMessage(`Wyczyszczono tabelę ${result.table_name}; usunięto ${result.deleted_count} rekordów.`);
      setConfirmations((current) => ({ ...current, [tableName]: '' }));
      await loadDiagnostics(true);
    } catch (requestError) {
      recordBackendFailure(requestError);
      setError(requestError instanceof Error ? requestError.message : 'Nie udało się wyczyścić tabeli.');
    } finally {
      setIsClearingTable(null);
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-violet-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-violet-800">
              <ShieldAlert className="h-3.5 w-3.5" />
              Narzędzia developerskie
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">Diagnostyka aplikacji</h1>
            <p className="mt-2 text-sm text-slate-600">
              Stan backendu, bazy danych, migracji i integracji. Czyszczenie usuwa dane trwale.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadDiagnostics(true)}
            disabled={isLoading || isRefreshing}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Odśwież
          </button>
        </div>
      </section>

      <section
        role="status"
        className={`rounded-2xl border p-5 ${
          backendStatus === 'online'
            ? 'border-emerald-200 bg-emerald-50'
            : backendStatus === 'offline' || backendStatus === 'error'
              ? 'border-rose-200 bg-rose-50'
              : 'border-slate-200 bg-white'
        }`}
      >
        <div className="flex items-start gap-3">
          {backendStatus === 'checking' ? (
            <Loader2 className="mt-0.5 h-5 w-5 animate-spin text-slate-500" />
          ) : backendStatus === 'online' ? (
            <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-700" />
          ) : (
            <XCircle className="mt-0.5 h-5 w-5 text-rose-700" />
          )}
          <div>
            <h2 className="font-semibold text-slate-900">
              Backend:{' '}
              {backendStatus === 'checking'
                ? 'sprawdzanie połączenia...'
                : backendStatus === 'online'
                  ? 'dostępny'
                  : backendStatus === 'offline'
                    ? 'nieosiągalny'
                    : 'odpowiada błędem'}
            </h2>
            <p className="mt-1 break-all text-sm text-slate-700">Adres API: {apiBaseUrl}</p>
            {backendError ? <p className="mt-2 text-sm text-rose-800">{backendError}</p> : null}
            {backendStatus === 'offline' ? (
              <p className="mt-2 text-sm text-slate-700">
                Uruchom backend z katalogu <code>backend</code>: <code>uvicorn app.main:app --reload</code>, a potem wybierz „Odśwież”.
              </p>
            ) : null}
          </div>
        </div>
      </section>

      {(error || message) && (
        <div
          role={error ? 'alert' : 'status'}
          className={`rounded-xl border p-3 text-sm ${
            error ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-emerald-200 bg-emerald-50 text-emerald-800'
          }`}
        >
          {error ?? message}
        </div>
      )}

      {isLoading && !diagnostics ? (
        <div className="flex items-center gap-2 rounded-2xl bg-white p-6 text-sm text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" /> Pobieranie diagnostyki...
        </div>
      ) : diagnostics ? (
        <>
          <section className="grid gap-4 md:grid-cols-2">
            <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2 font-semibold text-slate-900">
                <Server className="h-5 w-5 text-sky-700" /> Backend
              </div>
              <dl className="mt-4 space-y-2 text-sm">
                <InfoRow label="Stan" value="Działa" good />
                <InfoRow label="Aplikacja" value={`${diagnostics.app_name} ${diagnostics.app_version}`} />
                <InfoRow label="Python" value={diagnostics.python_version} />
              </dl>
            </article>
            <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2 font-semibold text-slate-900">
                <Database className="h-5 w-5 text-sky-700" /> Baza danych
              </div>
              <dl className="mt-4 space-y-2 text-sm">
                <InfoRow
                  label="Połączenie"
                  value={diagnostics.database.connected ? 'Połączono' : 'Brak połączenia'}
                  good={diagnostics.database.connected}
                />
                <InfoRow label="Typ" value={diagnostics.database.dialect} />
                <InfoRow label="Ścieżka / adres" value={diagnostics.database.location} />
                <InfoRow label="Migracje" value={migrationLabels[diagnostics.database.migration_status]} />
                <InfoRow label="Rewizja bazy" value={diagnostics.database.current_revision ?? 'brak'} />
                <InfoRow label="Najnowsza rewizja" value={diagnostics.database.head_revision ?? 'brak'} />
              </dl>
            </article>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Tabele bazy danych</h2>
            <p className="mt-1 text-sm text-slate-600">
              Czyszczenie wymaga przepisania nazwy tabeli i dodatkowego potwierdzenia. Tabele zależne trzeba wyczyścić wcześniej.
            </p>
            {!diagnostics.clear_enabled ? (
              <div className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                Czyszczenie jest wyłączone. Ustaw <code>DEV_TOOLS_ENABLED=true</code> w <code>backend/.env</code> i uruchom backend ponownie.
              </div>
            ) : null}
            <div className="mt-4 space-y-3">
              {diagnostics.tables.map((table) => (
                <div key={table.name} className="flex flex-col gap-3 rounded-xl border border-slate-200 p-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="font-mono text-sm font-semibold text-slate-900">{table.name}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      {!table.exists ? 'Tabela nie istnieje' : `${table.row_count ?? 0} rekordów`}
                    </div>
                  </div>
                  {table.clearable ? (
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        aria-label={`Potwierdź czyszczenie tabeli ${table.name}`}
                        value={confirmations[table.name] ?? ''}
                        onChange={(event) =>
                          setConfirmations((current) => ({ ...current, [table.name]: event.target.value }))
                        }
                        placeholder={`Wpisz: ${table.name}`}
                        disabled={!diagnostics.clear_enabled || backendStatus !== 'online' || isClearingTable !== null}
                        className="min-w-52 rounded-lg border border-slate-200 px-3 py-2 text-sm disabled:bg-slate-100"
                      />
                      <button
                        type="button"
                        onClick={() => void clearTable(table.name)}
                        disabled={
                          !diagnostics.clear_enabled ||
                          backendStatus !== 'online' ||
                          confirmations[table.name] !== table.name ||
                          isClearingTable !== null
                        }
                        className="inline-flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isClearingTable === table.name ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                        Wyczyść
                      </button>
                    </div>
                  ) : (
                    <span className="text-xs font-medium text-slate-500">
                      {table.exists ? 'Chroniona' : 'Niedostępna'}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </section>

          <section className="grid gap-4 md:grid-cols-2">
            <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="font-semibold text-slate-900">Integracje</h2>
              <dl className="mt-4 space-y-2 text-sm">
                <InfoRow label="Gemini" value={diagnostics.integrations.gemini ? 'Skonfigurowano' : 'Brak konfiguracji'} good={diagnostics.integrations.gemini} />
                <InfoRow label="Gmail IMAP/SMTP" value={diagnostics.integrations.gmail ? 'Skonfigurowano' : 'Brak konfiguracji'} good={diagnostics.integrations.gmail} />
              </dl>
              <p className="mt-3 text-xs text-slate-500">Sekrety nie są wyświetlane.</p>
            </article>
            <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="font-semibold text-slate-900">Ostatnie błędy i ostrzeżenia</h2>
              {diagnostics.recent_errors.length ? (
                <ul className="mt-3 space-y-2 text-sm">
                  {diagnostics.recent_errors.map((item, index) => (
                    <li key={`${item.timestamp}-${index}`} className="flex items-start gap-2 text-slate-700">
                      <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                      <span>
                        <span className="font-medium">{item.logger}</span>
                        <span className="block text-xs text-slate-500">{new Date(item.timestamp).toLocaleString()}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 inline-flex items-center gap-2 text-sm text-emerald-700">
                  <CheckCircle2 className="h-4 w-4" /> Brak błędów od uruchomienia backendu.
                </p>
              )}
              <p className="mt-3 text-xs text-slate-500">Lista jest tymczasowa i znika po restarcie backendu.</p>
            </article>
          </section>
        </>
      ) : null}
    </div>
  );
}

function InfoRow({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div className="flex flex-wrap justify-between gap-2">
      <dt className="text-slate-500">{label}</dt>
      <dd className={`break-all text-right font-medium ${good === undefined ? 'text-slate-800' : good ? 'text-emerald-700' : 'text-rose-700'}`}>
        {value}
      </dd>
    </div>
  );
}

export default DevPage;
