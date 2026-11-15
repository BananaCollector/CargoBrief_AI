import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  Loader2,
  MapPin,
  PackageCheck,
  RefreshCw,
  Sparkles,
  Trash2,
  Truck,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { fetchJson } from './api';
import { formatOrderAddress } from './orderAddress';

type Vehicle = {
  id: number;
  name: string;
};

type Order = {
  id: number;
  cargo_description: string;
  pickup_location: string;
  delivery_location: string;
  pickup_street: string | null;
  pickup_building_number: string | null;
  pickup_apartment: string | null;
  pickup_postal_code: string | null;
  delivery_street: string | null;
  delivery_building_number: string | null;
  delivery_apartment: string | null;
  delivery_postal_code: string | null;
  preferred_date: string | null;
  length_cm: number | null;
  width_cm: number | null;
  height_cm: number | null;
  weight_kg: number | null;
  quantity: number;
  status: 'new' | 'in_review' | 'approved';
  customer_email: string | null;
  customer_phone: string | null;
};

type Shipment = {
  id: number;
  scheduled_date: string;
  destination: string;
  vehicle: Vehicle;
  orders: Order[];
  total_weight_kg: number;
  total_volume_cm3: number;
  warnings: string[];
  notification_status: 'pending' | 'sending' | 'sent' | 'failed' | 'not_configured';
};

type ShipmentSuggestion = {
  order_ids: number[];
  destination: string;
  eligible: boolean;
  recommended_vehicle: Vehicle | null;
  total_weight_kg: number | null;
  total_volume_cm3: number | null;
  date_conflicts: number[];
  warnings: string[];
  message: string;
};

type ShipmentSuggestions = {
  mode: 'ai' | 'demo';
  groups: ShipmentSuggestion[];
};

const today = () => {
  const date = new Date();
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return localDate.toISOString().slice(0, 10);
};

function LogisticsPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [selectedOrderIds, setSelectedOrderIds] = useState<number[]>([]);
  const [scheduledDate, setScheduledDate] = useState(today);
  const [vehicleId, setVehicleId] = useState('');
  const [confirmDateOverride, setConfirmDateOverride] = useState(false);
  const [suggestions, setSuggestions] = useState<ShipmentSuggestions | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [activeShipmentId, setActiveShipmentId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    setWarning(null);
    try {
      const [ordersResponse, vehiclesResponse, shipmentsResponse] = await Promise.all([
        fetchJson<Order[]>('/api/v1/shipments/available-orders'),
        fetchJson<Vehicle[]>('/api/v1/vehicles'),
        fetchJson<Shipment[]>('/api/v1/shipments'),
      ]);
      setOrders(ordersResponse);
      setVehicles(vehiclesResponse);
      setShipments(shipmentsResponse);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : 'Nie udało się pobrać danych logistycznych.',
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
    const refreshId = window.setInterval(() => {
      void loadData();
    }, 15_000);
    return () => window.clearInterval(refreshId);
  }, []);

  const assignedOrderIds = useMemo(
    () => new Set(shipments.flatMap((shipment) => shipment.orders.map((order) => order.id))),
    [shipments],
  );
  const availableOrders = useMemo(
    () =>
      orders.filter(
        (order) => order.status === 'approved' && !assignedOrderIds.has(order.id),
      ),
    [assignedOrderIds, orders],
  );
  const selectedOrders = useMemo(
    () => availableOrders.filter((order) => selectedOrderIds.includes(order.id)),
    [availableOrders, selectedOrderIds],
  );
  const dateConflicts = selectedOrders.filter(
    (order) => order.preferred_date && order.preferred_date !== scheduledDate,
  );
  const missingCustomerEmails = selectedOrders.filter((order) => !order.customer_email);

  const toggleOrder = (orderId: number) => {
    setSelectedOrderIds((current) =>
      current.includes(orderId)
        ? current.filter((id) => id !== orderId)
        : [...current, orderId],
    );
    setSuggestions(null);
    setConfirmDateOverride(false);
    setError(null);
    setNotice(null);
    setWarning(null);
  };

  const suggestGroups = async () => {
    setIsSuggesting(true);
    setError(null);
    setNotice(null);
    try {
      const result = await fetchJson<ShipmentSuggestions>('/api/v1/shipments/suggest', {
        method: 'POST',
        body: JSON.stringify({ scheduled_date: scheduledDate, order_ids: selectedOrderIds }),
        headers: { 'Content-Type': 'application/json' },
      });
      setSuggestions(result);
    } catch (suggestError) {
      setError(
        suggestError instanceof Error
          ? suggestError.message
          : 'Nie udało się przygotować propozycji.',
      );
    } finally {
      setIsSuggesting(false);
    }
  };

  const applySuggestion = (suggestion: ShipmentSuggestion) => {
    setSelectedOrderIds(suggestion.order_ids);
    setVehicleId(suggestion.recommended_vehicle ? String(suggestion.recommended_vehicle.id) : '');
    setConfirmDateOverride(false);
    setNotice('Propozycja wybrana. Sprawdź datę i pojazd, a następnie utwórz wysyłkę.');
  };

  const createShipment = async () => {
    if (!vehicleId || selectedOrderIds.length === 0) return;
    setIsCreating(true);
    setError(null);
    setNotice(null);
    setWarning(null);
    try {
      const shipment = await fetchJson<Shipment>('/api/v1/shipments', {
        method: 'POST',
        body: JSON.stringify({
          scheduled_date: scheduledDate,
          vehicle_id: Number(vehicleId),
          order_ids: selectedOrderIds,
          confirm_date_override: confirmDateOverride,
        }),
        headers: { 'Content-Type': 'application/json' },
      });
      setSelectedOrderIds([]);
      setSuggestions(null);
      setConfirmDateOverride(false);
      await loadData();
      if (shipment.notification_status === 'not_configured') {
        setWarning(
          'Wysyłka została utworzona, ale e-maile nie zostały wysłane. Skonfiguruj Gmail w backendowym pliku .env.',
        );
      } else {
        setNotice('Wysyłka została utworzona. Powiadomienia zostaną wysłane automatycznie.');
      }
    } catch (createError) {
      setError(
        createError instanceof Error ? createError.message : 'Nie udało się utworzyć wysyłki.',
      );
    } finally {
      setIsCreating(false);
    }
  };

  const deleteShipment = async (shipmentId: number) => {
    if (!window.confirm('Usunąć wysyłkę i zwolnić przypisane do niej zlecenia?')) return;
    setActiveShipmentId(shipmentId);
    setError(null);
    setNotice(null);
    setWarning(null);
    try {
      await fetchJson<void>(`/api/v1/shipments/${shipmentId}`, { method: 'DELETE' });
      setNotice('Wysyłka została usunięta, a zlecenia wróciły do puli.');
      await loadData();
    } catch (deleteError) {
      setError(
        deleteError instanceof Error ? deleteError.message : 'Nie udało się usunąć wysyłki.',
      );
    } finally {
      setActiveShipmentId(null);
    }
  };

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-indigo-700">
          <Truck className="h-3.5 w-3.5" />
          Planowanie transportu
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Wysyłki i łączenie zleceń</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
          Wysyłka może zawierać zatwierdzone zlecenia do tego samego celu. Backend sprawdza
          wymiary, łączną wagę i przybliżoną objętość ładunku przed przypisaniem pojazdu.
          Kolejność wielu odbiorów nie jest optymalizowana.
        </p>
        <Link to="/employee" className="mt-5 inline-flex text-sm font-medium text-sky-700 hover:text-sky-800">
          Wróć do kolejki zleceń
        </Link>
      </section>

      {(error || notice) && (
        <div
          role={error ? 'alert' : 'status'}
          className={`rounded-2xl border p-4 text-sm ${
            error
              ? 'border-rose-200 bg-rose-50 text-rose-700'
              : 'border-emerald-200 bg-emerald-50 text-emerald-700'
          }`}
        >
          {error ?? notice}
        </div>
      )}
      {warning && (
        <div role="status" className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          {warning}
        </div>
      )}

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Zlecenia do zaplanowania</h2>
              <p className="mt-1 text-sm text-slate-500">Tylko zatwierdzone i nieprzypisane do wysyłki.</p>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-600">
              {availableOrders.length}
            </span>
          </div>

          {isLoading ? (
            <div className="flex items-center gap-2 py-8 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Ładowanie zleceń...
            </div>
          ) : availableOrders.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
              Brak zatwierdzonych zleceń gotowych do zaplanowania.
            </div>
          ) : (
            <div className="max-h-[34rem] space-y-3 overflow-y-auto pr-1">
              {availableOrders.map((order) => (
                <label
                  key={order.id}
                  className={`block cursor-pointer rounded-2xl border p-4 transition ${
                    selectedOrderIds.includes(order.id)
                      ? 'border-sky-300 bg-sky-50 ring-2 ring-sky-100'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selectedOrderIds.includes(order.id)}
                      onChange={() => toggleOrder(order.id)}
                      className="mt-1 h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-semibold text-slate-900">
                          #{order.id} · {order.cargo_description}
                        </span>
                        <span className="text-xs text-slate-500">
                          {order.preferred_date ? `Preferowana data: ${order.preferred_date}` : 'Termin elastyczny'}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-slate-600">
                        {formatOrderAddress(order, 'pickup')}
                        <ArrowRight className="mx-1 inline h-3.5 w-3.5" />
                        {formatOrderAddress(order, 'delivery')}
                      </p>
                      <p className="mt-2 text-xs text-slate-500">
                        {order.length_cm && order.width_cm && order.height_cm
                          ? `${order.length_cm} × ${order.width_cm} × ${order.height_cm} cm`
                          : 'Brak wymiarów'}
                        {' · '}
                        {order.weight_kg ? `${order.weight_kg * order.quantity} kg łącznie` : 'Brak wagi'}
                      </p>
                      {order.customer_phone ? (
                        <p className="mt-2 text-xs text-slate-500">Telefon klienta: {order.customer_phone}</p>
                      ) : null}
                      {!order.customer_email && (
                        <p className="mt-2 text-xs text-amber-800">
                          Brak adresu e-mail — uzupełnij go w kolejce zleceń przed utworzeniem wysyłki.
                        </p>
                      )}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-6">
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Nowa wysyłka</h2>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label>
                <span className="mb-2 block text-sm font-medium text-slate-700">Data wysyłki</span>
                <span className="relative block">
                  <CalendarDays className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    type="date"
                    value={scheduledDate}
                    onChange={(event) => {
                      setScheduledDate(event.target.value);
                      setConfirmDateOverride(false);
                      setSuggestions(null);
                    }}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-3 text-sm text-slate-800 outline-none focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
                  />
                </span>
              </label>

              <label>
                <span className="mb-2 block text-sm font-medium text-slate-700">Pojazd</span>
                <select
                  value={vehicleId}
                  onChange={(event) => setVehicleId(event.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
                >
                  <option value="">Wybierz pojazd</option>
                  {vehicles.map((vehicle) => (
                    <option key={vehicle.id} value={vehicle.id}>
                      {vehicle.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {dateConflicts.length > 0 && (
              <label className="mt-4 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                <input
                  type="checkbox"
                  checked={confirmDateOverride}
                  onChange={(event) => setConfirmDateOverride(event.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-amber-300 text-amber-600 focus:ring-amber-500"
                />
                <span>
                  Potwierdzam ręczną zmianę preferowanego terminu dla{' '}
                  {dateConflicts.map((order) => `#${order.id}`).join(', ')}.
                </span>
              </label>
            )}

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={suggestGroups}
                disabled={
                  selectedOrderIds.length === 0 ||
                  selectedOrderIds.length > 20 ||
                  isSuggesting ||
                  isCreating
                }
                className="inline-flex items-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2.5 text-sm font-medium text-indigo-700 transition hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSuggesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                {isSuggesting ? 'Analizuję...' : 'Propozycje AI'}
              </button>
              <button
                type="button"
                onClick={createShipment}
                disabled={
                  selectedOrderIds.length === 0 ||
                  !vehicleId ||
                  missingCustomerEmails.length > 0 ||
                  isCreating ||
                  isSuggesting ||
                  (dateConflicts.length > 0 && !confirmDateOverride)
                }
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {isCreating ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                Utwórz wysyłkę
              </button>
            </div>
            {selectedOrderIds.length > 20 && (
              <p className="mt-2 text-xs text-slate-500">
                Propozycje AI obsługują maksymalnie 20 zleceń naraz.
              </p>
            )}

            {suggestions && (
              <div className="mt-5 space-y-3 border-t border-slate-100 pt-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {suggestions.mode === 'ai' ? 'Propozycje Gemini' : 'Propozycje DEMO'}
                  {' · '}sprawdzone przez backend
                </p>
                {suggestions.groups.map((suggestion, index) => (
                  <div
                    key={`${suggestion.order_ids.join('-')}-${index}`}
                    className="rounded-xl border border-slate-200 bg-slate-50 p-3"
                  >
                    <p className="text-sm font-medium text-slate-800">{suggestion.message}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Zlecenia {suggestion.order_ids.map((id) => `#${id}`).join(', ')}
                      {' · '}cel: {suggestion.destination}
                      {suggestion.recommended_vehicle
                        ? ` · ${suggestion.recommended_vehicle.name}`
                        : ' · brak dopasowania'}
                    </p>
                    {suggestion.warnings.map((warning) => (
                      <p key={warning} className="mt-2 text-xs text-amber-800">{warning}</p>
                    ))}
                    <button
                      type="button"
                      disabled={!suggestion.eligible}
                      onClick={() => applySuggestion(suggestion)}
                      className="mt-3 rounded-lg bg-white px-3 py-1.5 text-xs font-medium text-sky-700 ring-1 ring-slate-200 hover:bg-sky-50 disabled:cursor-not-allowed disabled:text-slate-400"
                    >
                      Użyj propozycji
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-5 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Zaplanowane wysyłki</h2>
            <p className="mt-1 text-sm text-slate-500">Usuń wysyłkę, aby ponownie rozdzielić jej zlecenia.</p>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-600">{shipments.length}</span>
          <button
            type="button"
            onClick={() => void loadData()}
            disabled={isLoading}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Odśwież
          </button>
        </div>

        {shipments.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
            Nie utworzono jeszcze żadnej wysyłki.
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {shipments.map((shipment) => (
              <article key={shipment.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-slate-900">
                      Wysyłka #{shipment.id} · {shipment.scheduled_date}
                    </p>
                    <p className="mt-1 text-sm text-slate-600">
                      <MapPin className="mr-1 inline h-4 w-4" />
                      Cel: {shipment.destination} · {shipment.vehicle.name}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => deleteShipment(shipment.id)}
                    disabled={activeShipmentId !== null}
                    aria-label={`Usuń wysyłkę ${shipment.id}`}
                    className="rounded-lg p-2 text-rose-600 hover:bg-rose-100 disabled:opacity-50"
                  >
                    {activeShipmentId === shipment.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </div>
                <div className="mt-3 space-y-2">
                  {shipment.orders.map((order) => (
                    <div key={order.id} className="flex items-center justify-between gap-2 rounded-xl bg-white px-3 py-2 text-sm">
                      <span className="font-medium text-slate-700">
                        #{order.id} · {order.cargo_description}
                      </span>
                      <span className="text-right text-xs text-slate-500">
                        {formatOrderAddress(order, 'pickup')}
                      </span>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-xs text-slate-600">
                  <PackageCheck className="mr-1 inline h-4 w-4" />
                  {shipment.orders.length} zleceń · {shipment.total_weight_kg} kg ·{' '}
                  {Math.round(shipment.total_volume_cm3 / 1_000_000 * 100) / 100} m³
                </p>
                <p className="mt-2 text-xs font-medium text-slate-700">
                  Powiadomienia:{' '}
                  {shipment.notification_status === 'sent'
                    ? 'wysłane'
                    : shipment.notification_status === 'pending' ||
                        shipment.notification_status === 'sending'
                      ? 'oczekują na wysłanie'
                      : shipment.notification_status === 'failed'
                        ? 'błąd wysyłki'
                        : 'brak konfiguracji Gmail'}
                </p>
                {shipment.warnings.map((warning) => (
                  <p key={warning} className="mt-2 text-xs text-amber-800">{warning}</p>
                ))}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default LogisticsPage;
