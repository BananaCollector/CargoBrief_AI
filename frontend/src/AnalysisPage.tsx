import { useState } from 'react';
import { ArrowRight, CheckCircle2, Loader2, RefreshCw, ShieldCheck, Truck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { fetchJson } from './api';
import { formatOrderAddress } from './orderAddress';

type Vehicle = {
  id: number;
  name: string;
  max_payload_kg: number;
};

type AnalysisOrder = {
  cargo_description?: string;
  length_cm?: number | null;
  width_cm?: number | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  quantity?: number;
  pickup_location?: string;
  delivery_location?: string;
  pickup_street?: string | null;
  pickup_building_number?: string | null;
  pickup_apartment?: string | null;
  pickup_postal_code?: string | null;
  delivery_street?: string | null;
  delivery_building_number?: string | null;
  delivery_apartment?: string | null;
  delivery_postal_code?: string | null;
  customer_phone?: string | null;
  preferred_date?: string | null;
};

type AnalysisResult = {
  order: AnalysisOrder;
  missing_fields: string[];
  ambiguities: string[];
  mode: 'ai' | 'demo';
};

type VehicleMatch = {
  status: 'confirmed' | 'missing_data' | 'no_match';
  recommended_vehicle: Vehicle | null;
  total_weight_kg: number | null;
  message: string;
  simulation_note: string;
};

const demoMessage =
  'Dzień dobry, proszę o przewóz kanapy o wymiarach 220 × 90 × 85 cm i wadze 250 kg z ul. Długiej 10/3, 80-831 Gdańsk na ul. Floriańską 12, 31-021 Kraków. Telefon: +48 600 700 800.';

function AnalysisPage() {
  const navigate = useNavigate();
  const [message, setMessage] = useState(demoMessage);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [vehicleMatch, setVehicleMatch] = useState<VehicleMatch | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeMessage = async () => {
    setIsAnalyzing(true);
    setError(null);
    setAnalysis(null);
    setVehicleMatch(null);

    try {
      const result = await fetchJson<AnalysisResult>('/api/v1/ai/analyze', {
        method: 'POST',
        body: JSON.stringify({ message }),
        headers: { 'Content-Type': 'application/json' },
      });
      setAnalysis(result);

      const match = await fetchJson<VehicleMatch>('/api/v1/vehicles/match', {
        method: 'POST',
        body: JSON.stringify({
          length_cm: result.order.length_cm ?? null,
          width_cm: result.order.width_cm ?? null,
          height_cm: result.order.height_cm ?? null,
          weight_kg: result.order.weight_kg ?? null,
          quantity: result.order.quantity ?? 1,
        }),
        headers: { 'Content-Type': 'application/json' },
      });
      setVehicleMatch(match);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Nie udało się przeanalizować wiadomości.',
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-5 inline-flex items-center gap-2 rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-sky-700">
          <ShieldCheck className="h-3.5 w-3.5" />
          Demonstracja automatyzacji
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          Analiza wiadomości i dopasowanie pojazdu
        </h1>
        <p className="mt-3 max-w-3xl text-slate-600">
          Wklej wiadomość klienta, aby zobaczyć ekstrakcję danych i deterministyczne dopasowanie pojazdu.
          Wynik jest tylko propozycją — zlecenie wymaga zatwierdzenia przez pracownika.
        </p>
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          rows={7}
          placeholder="Wklej treść wiadomości klienta..."
          className="mt-6 w-full resize-y rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
        />
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void analyzeMessage()}
            disabled={isAnalyzing || !message.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-sky-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {isAnalyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            {isAnalyzing ? 'Analizuję...' : 'Uruchom analizę'}
          </button>
          <button
            type="button"
            onClick={() => {
              setMessage(demoMessage);
              setAnalysis(null);
              setVehicleMatch(null);
              setError(null);
            }}
            className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            Wczytaj przykładową wiadomość
          </button>
        </div>
        {error ? (
          <div role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}
      </section>

      {analysis ? (
        <section className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-900">Dane odczytane z wiadomości</h2>
              <span className="rounded-full bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-700">
                {analysis.mode === 'ai' ? 'Gemini' : 'DEMO'}
              </span>
            </div>
            <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
              <DataItem label="Ładunek" value={analysis.order.cargo_description} />
              <DataItem
                label="Odbiór"
                value={formatOrderAddress(analysis.order, 'pickup') || '—'}
              />
              <DataItem
                label="Dostawa"
                value={formatOrderAddress(analysis.order, 'delivery') || '—'}
              />
              <DataItem
                label="Wymiary"
                value={
                  analysis.order.length_cm && analysis.order.width_cm && analysis.order.height_cm
                    ? `${analysis.order.length_cm} × ${analysis.order.width_cm} × ${analysis.order.height_cm} cm`
                    : 'Brak pełnych wymiarów'
                }
              />
              <DataItem label="Waga" value={analysis.order.weight_kg ? `${analysis.order.weight_kg} kg` : 'Brak danych'} />
              <DataItem label="Ilość" value={analysis.order.quantity ?? 1} />
              <DataItem label="Preferowana data" value={analysis.order.preferred_date || '—'} />
              <DataItem label="Telefon klienta" value={analysis.order.customer_phone || 'Brak danych'} />
            </dl>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <NoticeList title="Brakujące dane" values={analysis.missing_fields} />
              <NoticeList title="Wątpliwości" values={analysis.ambiguities} />
            </div>

            <button
              type="button"
              onClick={() =>
                navigate('/employee', {
                  state: { analysisDraft: { order: analysis.order, originalMessage: message } },
                })
              }
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-700"
            >
              Utwórz zlecenie z analizy
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-5 flex items-center gap-2">
              <Truck className="h-5 w-5 text-sky-700" />
              <h2 className="text-lg font-semibold text-slate-900">Dopasowanie pojazdu</h2>
            </div>
            {vehicleMatch ? (
              <>
                <div
                  className={`rounded-2xl border p-4 ${
                    vehicleMatch.status === 'confirmed'
                      ? 'border-emerald-200 bg-emerald-50'
                      : 'border-amber-200 bg-amber-50'
                  }`}
                >
                  <p className="font-semibold text-slate-900">
                    {vehicleMatch.recommended_vehicle?.name ?? vehicleMatch.message}
                  </p>
                  {vehicleMatch.total_weight_kg !== null ? (
                    <p className="mt-2 text-sm text-slate-700">
                      Łączna waga: {vehicleMatch.total_weight_kg} kg
                    </p>
                  ) : null}
                  {vehicleMatch.recommended_vehicle ? (
                    <p className="mt-1 text-sm text-slate-700">
                      Ładowność pojazdu: {vehicleMatch.recommended_vehicle.max_payload_kg} kg
                    </p>
                  ) : null}
                </div>
                <p className="mt-4 text-sm text-slate-600">{vehicleMatch.simulation_note}</p>
              </>
            ) : (
              <p className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
                Nie udało się pobrać dopasowania pojazdu.
              </p>
            )}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function DataItem({ label, value }: { label: string; value: string | number | undefined }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 font-medium text-slate-800">{value ?? '—'}</dd>
    </div>
  );
}

function NoticeList({ title, values }: { title: string; values: string[] }) {
  return (
    <div className="rounded-xl border border-slate-200 p-3">
      <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
      {values.length ? (
        <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-slate-600">
          {values.map((value, index) => <li key={`${index}-${value}`}>{value}</li>)}
        </ul>
      ) : (
        <p className="mt-2 inline-flex items-center gap-1 text-sm text-emerald-700">
          <CheckCircle2 className="h-4 w-4" />
          Brak
        </p>
      )}
    </div>
  );
}

export default AnalysisPage;
