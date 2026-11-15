import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  Clipboard,
  Code2,
  Loader2,
  MapPin,
  PencilLine,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  Truck,
} from 'lucide-react';
import { Link, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { fetchJson } from './api';
import AnalysisPage from './AnalysisPage';
import DevPage from './DevPage';
import LogisticsPage from './LogisticsPage';
import { formatOrderAddress } from './orderAddress';

type Vehicle = {
  id: number;
  name: string;
  max_length_cm: number;
  max_width_cm: number;
  max_height_cm: number;
  max_payload_kg: number;
};

type MatchStatus = 'confirmed' | 'missing_data' | 'no_match';

type VehicleMatch = {
  status: MatchStatus;
  recommended_vehicle: Vehicle | null;
  total_weight_kg: number | null;
  missing_fields: string[];
  message: string;
  simulation_note: string;
};

type OrderStatus = 'new' | 'in_review' | 'approved';

type OrderFormState = {
  id?: number;
  cargo_description: string;
  length_cm: string;
  width_cm: string;
  height_cm: string;
  weight_kg: string;
  quantity: number;
  pickup_location: string;
  delivery_location: string;
  pickup_street: string;
  pickup_building_number: string;
  pickup_apartment: string;
  pickup_postal_code: string;
  delivery_street: string;
  delivery_building_number: string;
  delivery_apartment: string;
  delivery_postal_code: string;
  preferred_date: string;
  preferred_time: string;
  pickup_floor: string;
  delivery_floor: string;
  pickup_has_elevator: boolean | null;
  delivery_has_elevator: boolean | null;
  notes: string;
  original_message: string;
  customer_email: string;
  customer_phone: string;
  status: OrderStatus;
};

type OrderRecord = Omit<
  OrderFormState,
  | 'length_cm'
  | 'width_cm'
  | 'height_cm'
  | 'weight_kg'
  | 'preferred_date'
  | 'preferred_time'
  | 'pickup_floor'
  | 'delivery_floor'
  | 'notes'
  | 'original_message'
  | 'customer_email'
  | 'customer_phone'
  | 'pickup_street'
  | 'pickup_building_number'
  | 'pickup_apartment'
  | 'pickup_postal_code'
  | 'delivery_street'
  | 'delivery_building_number'
  | 'delivery_apartment'
  | 'delivery_postal_code'
  | 'cargo_description'
  | 'pickup_location'
  | 'delivery_location'
> & {
  id: number;
  cargo_description: string | null;
  pickup_location: string | null;
  delivery_location: string | null;
  length_cm: number | null;
  width_cm: number | null;
  height_cm: number | null;
  weight_kg: number | null;
  preferred_date: string | null;
  preferred_time: string | null;
  pickup_floor: number | null;
  delivery_floor: number | null;
  notes: string | null;
  original_message: string | null;
  customer_email: string | null;
  customer_phone: string | null;
  pickup_street: string | null;
  pickup_building_number: string | null;
  pickup_apartment: string | null;
  pickup_postal_code: string | null;
  delivery_street: string | null;
  delivery_building_number: string | null;
  delivery_apartment: string | null;
  delivery_postal_code: string | null;
  created_at: string;
  updated_at: string;
  match: VehicleMatch;
};

type AIAnalyzeResult = {
  order: Partial<OrderFormState>;
  missing_fields: string[];
  ambiguities: string[];
  mode: 'ai' | 'demo';
};

type IncomingEmail = {
  id: number;
  sender_email: string | null;
  subject: string;
  body: string;
  status: 'pending_analysis' | 'ready' | 'converted';
  analysis: AIAnalyzeResult | null;
  converted_order_id?: number | null;
};

type EmailInboxFilter = {
  enabled: boolean;
  subject_phrase: string;
};

const statusLabels: Record<OrderStatus, string> = {
  new: 'Nowe',
  in_review: 'W trakcie weryfikacji',
  approved: 'Zatwierdzone',
};

const emptyForm: OrderFormState = {
  cargo_description: '',
  length_cm: '',
  width_cm: '',
  height_cm: '',
  weight_kg: '',
  quantity: 1,
  pickup_location: '',
  delivery_location: '',
  pickup_street: '',
  pickup_building_number: '',
  pickup_apartment: '',
  pickup_postal_code: '',
  delivery_street: '',
  delivery_building_number: '',
  delivery_apartment: '',
  delivery_postal_code: '',
  preferred_date: '',
  preferred_time: '',
  pickup_floor: '',
  delivery_floor: '',
  pickup_has_elevator: null,
  delivery_has_elevator: null,
  notes: '',
  original_message: '',
  customer_email: '',
  customer_phone: '',
  status: 'new',
};

const toNumber = (value: string | number | null | undefined) => {
  if (value === '' || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const clampNumberString = (value: string) => (value === '' ? '' : String(value).replace(/,/g, '.'));

function toFormState(order: Partial<OrderRecord> | Partial<AIAnalyzeResult['order']> | null | undefined): OrderFormState {
  const base = { ...emptyForm };

  if (!order) return base;

  return {
    ...base,
    cargo_description: order.cargo_description ?? '',
    length_cm: order.length_cm == null ? '' : clampNumberString(String(order.length_cm)),
    width_cm: order.width_cm == null ? '' : clampNumberString(String(order.width_cm)),
    height_cm: order.height_cm == null ? '' : clampNumberString(String(order.height_cm)),
    weight_kg: order.weight_kg == null ? '' : clampNumberString(String(order.weight_kg)),
    quantity: order.quantity ?? 1,
    pickup_location: order.pickup_location ?? '',
    delivery_location: order.delivery_location ?? '',
    pickup_street: order.pickup_street ?? '',
    pickup_building_number: order.pickup_building_number ?? '',
    pickup_apartment: order.pickup_apartment ?? '',
    pickup_postal_code: order.pickup_postal_code ?? '',
    delivery_street: order.delivery_street ?? '',
    delivery_building_number: order.delivery_building_number ?? '',
    delivery_apartment: order.delivery_apartment ?? '',
    delivery_postal_code: order.delivery_postal_code ?? '',
    preferred_date: order.preferred_date ?? '',
    preferred_time: order.preferred_time ?? '',
    pickup_floor: order.pickup_floor == null ? '' : String(order.pickup_floor),
    delivery_floor: order.delivery_floor == null ? '' : String(order.delivery_floor),
    pickup_has_elevator: order.pickup_has_elevator ?? null,
    delivery_has_elevator: order.delivery_has_elevator ?? null,
    notes: order.notes ?? '',
    original_message: order.original_message ?? '',
    customer_email: order.customer_email ?? '',
    customer_phone: order.customer_phone ?? '',
    status: order.status ?? 'new',
  };
}

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
            <Link to="/employee" className="transition hover:text-slate-900">
              Panel pracownika
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/analysis" className="transition hover:text-slate-900">
              Analiza
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/logistics" className="transition hover:text-slate-900">
              Logistyka
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/dev" className="inline-flex items-center gap-1 transition hover:text-slate-900">
              <Code2 className="h-4 w-4" />
              Dev
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/employee" element={<EmployeePage />} />
          <Route path="/analysis" element={<AnalysisPage />} />
          <Route path="/logistics" element={<LogisticsPage />} />
          <Route path="/dev" element={<DevPage />} />
        </Routes>
      </main>
    </div>
  );
}

function HomePage() {
  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
        <div className="mb-5 inline-flex items-center gap-2 rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-sky-700">
          <ShieldCheck className="h-3.5 w-3.5" />
          CargoBrief AI
        </div>
        <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-slate-900">
          Zgłoszenia transportowe uporządkowane w jednym miejscu.
        </h1>
        <p className="mt-4 max-w-2xl text-base text-slate-600">
          Wiadomości klientów stają się czytelnymi zleceniami, a pracownik weryfikuje dane i zatwierdza
          każde z nich przed zaplanowaniem transportu.
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <Link
            to="/employee"
            className="group rounded-2xl border border-sky-200 bg-sky-50 p-5 transition hover:border-sky-300 hover:bg-sky-100"
          >
            <h2 className="font-semibold text-slate-900">Panel pracownika</h2>
            <p className="mt-2 text-sm text-slate-600">
              Weryfikuj i edytuj zgłoszenia, obsługuj e-maile i dodawaj zlecenia ręcznie.
            </p>
            <span className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-sky-700">
              Otwórz panel <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
            </span>
          </Link>
          <Link
            to="/analysis"
            className="group rounded-2xl border border-slate-200 bg-slate-50 p-5 transition hover:border-slate-300 hover:bg-slate-100"
          >
            <h2 className="font-semibold text-slate-900">Analiza wiadomości</h2>
            <p className="mt-2 text-sm text-slate-600">
              Zobacz, jak system wydobywa dane z wiadomości i dobiera pojazd.
            </p>
            <span className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-sky-700">
              Zobacz demonstrację <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
            </span>
          </Link>
          <Link
            to="/logistics"
            className="group rounded-2xl border border-slate-200 bg-slate-50 p-5 transition hover:border-slate-300 hover:bg-slate-100"
          >
            <h2 className="font-semibold text-slate-900">Logistyka</h2>
            <p className="mt-2 text-sm text-slate-600">
              Planuj wysyłki z zatwierdzonych zleceń i śledź powiadomienia.
            </p>
            <span className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-sky-700">
              Przejdź do logistyki <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
            </span>
          </Link>
        </div>
      </section>
    </div>
  );
}

function EmployeePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [incomingEmails, setIncomingEmails] = useState<IncomingEmail[]>([]);
  const [emailFilterEnabled, setEmailFilterEnabled] = useState(false);
  const [emailFilterPhrase, setEmailFilterPhrase] = useState('');
  const [isSavingEmailFilter, setIsSavingEmailFilter] = useState(false);
  const [orderStatusFilter, setOrderStatusFilter] = useState<'all' | OrderStatus>('all');
  const [orderSearch, setOrderSearch] = useState('');
  const [targetOrderId, setTargetOrderId] = useState<number | null>(null);
  const [highlightedOrderId, setHighlightedOrderId] = useState<number | null>(null);
  const [form, setForm] = useState<OrderFormState>(emptyForm);
  const [isManualFormOpen, setIsManualFormOpen] = useState(false);
  const [isLoadingOrders, setIsLoadingOrders] = useState(false);
  const [isUpdatingOrderId, setIsUpdatingOrderId] = useState<number | null>(null);
  const [inlineEditingOrderId, setInlineEditingOrderId] = useState<number | null>(null);
  const [inlineForm, setInlineForm] = useState<OrderFormState | null>(null);
  const [copyError, setCopyError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [orderListError, setOrderListError] = useState<string | null>(null);
  const [orderListSuccess, setOrderListSuccess] = useState<string | null>(null);
  const [isAnalyzingEmailId, setIsAnalyzingEmailId] = useState<number | null>(null);
  const [isSyncingEmails, setIsSyncingEmails] = useState(false);
  const [emailActionError, setEmailActionError] = useState<string | null>(null);
  const [emailActionSuccess, setEmailActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    const navigationState = location.state as {
      analysisDraft?: { order: Partial<OrderFormState>; originalMessage: string };
    } | null;
    if (navigationState?.analysisDraft) {
      setForm(toFormState({
        ...navigationState.analysisDraft.order,
        original_message: navigationState.analysisDraft.originalMessage,
        customer_email: 'test@email.com',
      }));
      setIsManualFormOpen(true);
      setSubmitError(null);
      setSuccessMessage('Sprawdź dane z analizy i uzupełnij brakujące informacje przed zapisaniem zlecenia.');
    } else {
      return;
    }
    navigate(location.pathname, { replace: true, state: null });
  }, [location.pathname, location.state, navigate]);

  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoadingOrders(true);
        setOrderListError(null);
        const [vehiclesResponse, ordersResponse, emailsResponse] = await Promise.all([
          fetchJson<Vehicle[]>('/api/v1/vehicles'),
          fetchJson<OrderRecord[]>('/api/v1/orders'),
          fetchJson<IncomingEmail[]>('/api/v1/email/inbox'),
        ]);
        setVehicles(vehiclesResponse);
        setOrders(ordersResponse);
        setIncomingEmails(emailsResponse);
      } catch (error) {
        setOrderListError(
          error instanceof Error ? error.message : 'Nie udało się pobrać zleceń.',
        );
      } finally {
        setIsLoadingOrders(false);
      }
    };

    void loadData();
    const refreshId = window.setInterval(() => {
      void loadData();
    }, 30_000);
    return () => window.clearInterval(refreshId);
  }, []);

  useEffect(() => {
    fetchJson<EmailInboxFilter>('/api/v1/email/inbox/filter')
      .then((filter) => {
        setEmailFilterEnabled(filter.enabled);
        setEmailFilterPhrase(filter.subject_phrase);
      })
      .catch((error: unknown) => {
        setEmailActionError(error instanceof Error ? error.message : 'Nie udało się pobrać filtra poczty.');
      });
  }, []);

  const filteredOrders = useMemo(
    () => {
      const query = orderSearch.trim().toLocaleLowerCase('pl');
      return orders.filter((order) => {
        const matchesStatus = orderStatusFilter === 'all' || order.status === orderStatusFilter;
        if (!matchesStatus || !query) return matchesStatus;
        const searchableValues = [
          String(order.id),
          order.cargo_description,
          order.pickup_location,
          order.delivery_location,
          formatOrderAddress(order, 'pickup'),
          formatOrderAddress(order, 'delivery'),
          order.customer_email,
          order.customer_phone,
          order.original_message,
        ];
        return searchableValues.some((value) =>
          value?.toLocaleLowerCase('pl').includes(query),
        );
      });
    },
    [orderSearch, orderStatusFilter, orders],
  );

  useEffect(() => {
    if (targetOrderId === null || !filteredOrders.some((order) => order.id === targetOrderId)) return;
    const target = document.getElementById(`order-${targetOrderId}`);
    target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setHighlightedOrderId(targetOrderId);
    setTargetOrderId(null);
    const timeoutId = window.setTimeout(() => setHighlightedOrderId(null), 2500);
    return () => window.clearTimeout(timeoutId);
  }, [filteredOrders, targetOrderId]);

  const updateField = <K extends keyof OrderFormState>(key: K, value: OrderFormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
    setSubmitError(null);
    setSuccessMessage(null);
  };

  const resetForm = () => {
    setForm(emptyForm);
    setIsManualFormOpen(false);
    setSubmitError(null);
    setSuccessMessage(null);
  };

  const saveOrder = async () => {
    setIsSaving(true);
    setSubmitError(null);
    setSuccessMessage(null);

    try {
      const payload = {
        cargo_description: form.cargo_description.trim(),
        length_cm: toNumber(form.length_cm),
        width_cm: toNumber(form.width_cm),
        height_cm: toNumber(form.height_cm),
        weight_kg: toNumber(form.weight_kg),
        quantity: Number(form.quantity || 1),
        pickup_location: form.pickup_location.trim(),
        delivery_location: form.delivery_location.trim(),
        pickup_street: form.pickup_street.trim() || null,
        pickup_building_number: form.pickup_building_number.trim() || null,
        pickup_apartment: form.pickup_apartment.trim() || null,
        pickup_postal_code: form.pickup_postal_code.trim() || null,
        delivery_street: form.delivery_street.trim() || null,
        delivery_building_number: form.delivery_building_number.trim() || null,
        delivery_apartment: form.delivery_apartment.trim() || null,
        delivery_postal_code: form.delivery_postal_code.trim() || null,
        preferred_date: form.preferred_date || null,
        preferred_time: form.preferred_time || null,
        pickup_floor: toNumber(form.pickup_floor),
        delivery_floor: toNumber(form.delivery_floor),
        pickup_has_elevator: form.pickup_has_elevator,
        delivery_has_elevator: form.delivery_has_elevator,
        notes: form.notes.trim() || null,
        original_message: form.original_message.trim() || null,
        customer_email: form.customer_email.trim() || null,
        customer_phone: form.customer_phone.trim() || null,
      };

      const savedOrder = form.id
        ? await fetchJson<OrderRecord>(`/api/v1/orders/${form.id}`, {
            method: 'PUT',
            body: JSON.stringify({ ...payload, status: form.status }),
            headers: { 'Content-Type': 'application/json' },
          })
        : await fetchJson<OrderRecord>('/api/v1/orders', {
            method: 'POST',
            body: JSON.stringify(payload),
            headers: { 'Content-Type': 'application/json' },
          });

      setOrders((current) => {
        const filtered = current.filter((order) => order.id !== savedOrder.id);
        return [savedOrder, ...filtered].sort((a, b) => b.created_at.localeCompare(a.created_at));
      });
      setSuccessMessage(
        form.id ? 'Zlecenie zostało zaktualizowane.' : 'Zlecenie zostało zapisane.',
      );
      setForm(emptyForm);
      setIsManualFormOpen(false);
      setOrderListSuccess(form.id ? 'Zlecenie zostało zaktualizowane.' : 'Zlecenie zostało zapisane.');
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Nie udało się zapisać zlecenia.');
    } finally {
      setIsSaving(false);
    }
  };

  const startInlineEdit = (order: OrderRecord) => {
    setInlineEditingOrderId(order.id);
    setInlineForm(toFormState(order));
    setOrderListError(null);
    setOrderListSuccess(null);
    setCopyError(null);
  };

  const cancelInlineEdit = () => {
    setInlineEditingOrderId(null);
    setInlineForm(null);
    setCopyError(null);
  };

  const updateInlineField = <K extends keyof OrderFormState>(key: K, value: OrderFormState[K]) => {
    setInlineForm((current) => current ? { ...current, [key]: value } : current);
  };

  const saveInlineEdit = async (order: OrderRecord) => {
    if (!inlineForm) return;
    setIsUpdatingOrderId(order.id);
    setOrderListError(null);
    setOrderListSuccess(null);
    try {
      const updatedOrder = await fetchJson<OrderRecord>(`/api/v1/orders/${order.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          cargo_description: inlineForm.cargo_description.trim() || null,
          length_cm: toNumber(inlineForm.length_cm),
          width_cm: toNumber(inlineForm.width_cm),
          height_cm: toNumber(inlineForm.height_cm),
          weight_kg: toNumber(inlineForm.weight_kg),
          quantity: Number(inlineForm.quantity || 1),
          pickup_location: inlineForm.pickup_location.trim() || null,
          delivery_location: inlineForm.delivery_location.trim() || null,
          pickup_street: inlineForm.pickup_street.trim() || null,
          pickup_building_number: inlineForm.pickup_building_number.trim() || null,
          pickup_apartment: inlineForm.pickup_apartment.trim() || null,
          pickup_postal_code: inlineForm.pickup_postal_code.trim() || null,
          delivery_street: inlineForm.delivery_street.trim() || null,
          delivery_building_number: inlineForm.delivery_building_number.trim() || null,
          delivery_apartment: inlineForm.delivery_apartment.trim() || null,
          delivery_postal_code: inlineForm.delivery_postal_code.trim() || null,
          preferred_date: inlineForm.preferred_date || null,
          preferred_time: inlineForm.preferred_time || null,
          pickup_floor: toNumber(inlineForm.pickup_floor),
          delivery_floor: toNumber(inlineForm.delivery_floor),
          pickup_has_elevator: inlineForm.pickup_has_elevator,
          delivery_has_elevator: inlineForm.delivery_has_elevator,
          notes: inlineForm.notes.trim() || null,
          original_message: inlineForm.original_message.trim() || null,
          customer_email: order.customer_email,
          customer_phone: inlineForm.customer_phone.trim() || null,
          status: inlineForm.status,
        }),
        headers: { 'Content-Type': 'application/json' },
      });
      setOrders((current) =>
        current.map((currentOrder) => currentOrder.id === updatedOrder.id ? updatedOrder : currentOrder),
      );
      setOrderListSuccess(`Zlecenie #${order.id} zostało zaktualizowane.`);
      cancelInlineEdit();
    } catch (error) {
      setOrderListError(error instanceof Error ? error.message : 'Nie udało się zapisać zlecenia.');
    } finally {
      setIsUpdatingOrderId(null);
    }
  };

  const copyCustomerEmail = async (email: string) => {
    try {
      await navigator.clipboard.writeText(email);
      setCopyError(null);
      setOrderListSuccess('Adres e-mail skopiowano do schowka.');
    } catch {
      setCopyError('Nie udało się skopiować adresu e-mail. Sprawdź uprawnienia schowka przeglądarki.');
    }
  };

  const scrollToOrder = async (orderId: number) => {
    setOrderListError(null);
    if (!orders.some((order) => order.id === orderId)) {
      try {
        const order = await fetchJson<OrderRecord>(`/api/v1/orders/${orderId}`);
        setOrders((current) => [order, ...current.filter((item) => item.id !== order.id)]);
      } catch (error) {
        setOrderListError(
          error instanceof Error ? error.message : `Nie znaleziono zlecenia #${orderId}.`,
        );
        return;
      }
    }
    setOrderStatusFilter('all');
    setOrderSearch('');
    setTargetOrderId(orderId);
    document.getElementById('review-queue')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const analyzeIncomingEmail = async (incomingEmailId: number) => {
    setIsAnalyzingEmailId(incomingEmailId);
    setEmailActionError(null);
    setEmailActionSuccess(null);
    try {
      const updatedEmail = await fetchJson<IncomingEmail>(
        `/api/v1/email/inbox/${incomingEmailId}/analyze`,
        { method: 'POST' },
      );
      if (updatedEmail.status === 'converted') {
        const [refreshedEmails, refreshedOrders] = await Promise.all([
          fetchJson<IncomingEmail[]>('/api/v1/email/inbox'),
          fetchJson<OrderRecord[]>('/api/v1/orders'),
        ]);
        setIncomingEmails(refreshedEmails);
        setOrders(refreshedOrders);
        setEmailActionSuccess(`Wiadomość #${incomingEmailId} przeanalizowano i dodano do kolejki weryfikacji.`);
      } else {
        setIncomingEmails((current) =>
          current.map((incomingEmail) =>
            incomingEmail.id === updatedEmail.id ? updatedEmail : incomingEmail,
          ),
        );
        setEmailActionSuccess(`Wiadomość #${incomingEmailId} została przeanalizowana.`);
      }
    } catch (error) {
      setEmailActionError(
        error instanceof Error ? error.message : 'Nie udało się przeanalizować wiadomości.',
      );
    } finally {
      setIsAnalyzingEmailId(null);
    }
  };

  const syncIncomingEmails = async () => {
    setIsSyncingEmails(true);
    setEmailActionError(null);
    setEmailActionSuccess(null);
    try {
      const result = await fetchJson<{ imported_count: number; analyzed_count: number }>('/api/v1/email/inbox/sync', {
        method: 'POST',
      });
      const [refreshedEmails, refreshedOrders] = await Promise.all([
        fetchJson<IncomingEmail[]>('/api/v1/email/inbox'),
        fetchJson<OrderRecord[]>('/api/v1/orders'),
      ]);
      setIncomingEmails(refreshedEmails);
      setOrders(refreshedOrders);
      setEmailActionSuccess(
        result.analyzed_count > 0
          ? `Pobrano ${result.imported_count} wiadomości; ${result.analyzed_count} przeanalizowano i dodano do kolejki weryfikacji.`
          : result.imported_count > 0
            ? `Pobrano ${result.imported_count} wiadomości. Oczekują na analizę przez Gemini.`
          : 'Sprawdzono skrzynkę. Brak nowych wiadomości.',
      );
    } catch (error) {
      setEmailActionError(error instanceof Error ? error.message : 'Nie udało się sprawdzić poczty.');
    } finally {
      setIsSyncingEmails(false);
    }
  };

  const saveEmailInboxFilter = async () => {
    setIsSavingEmailFilter(true);
    setEmailActionError(null);
    setEmailActionSuccess(null);
    try {
      const savedFilter = await fetchJson<EmailInboxFilter>('/api/v1/email/inbox/filter', {
        method: 'PUT',
        body: JSON.stringify({
          enabled: emailFilterEnabled,
          subject_phrase: emailFilterPhrase,
        }),
        headers: { 'Content-Type': 'application/json' },
      });
      setEmailFilterEnabled(savedFilter.enabled);
      setEmailFilterPhrase(savedFilter.subject_phrase);
      setEmailActionSuccess(
        savedFilter.enabled
          ? `Filtr aktywny: temat musi zawierać „${savedFilter.subject_phrase}”.`
          : 'Filtr tematu został wyłączony.',
      );
    } catch (error) {
      setEmailActionError(error instanceof Error ? error.message : 'Nie udało się zapisać filtra poczty.');
    } finally {
      setIsSavingEmailFilter(false);
    }
  };

  const updateOrderStatus = async (order: OrderRecord, nextStatus: OrderStatus) => {
    setIsUpdatingOrderId(order.id);
    setOrderListError(null);
    setOrderListSuccess(null);

    const payload = {
      cargo_description: order.cargo_description,
      length_cm: order.length_cm,
      width_cm: order.width_cm,
      height_cm: order.height_cm,
      weight_kg: order.weight_kg,
      quantity: order.quantity,
      pickup_location: order.pickup_location,
      delivery_location: order.delivery_location,
      pickup_street: order.pickup_street,
      pickup_building_number: order.pickup_building_number,
      pickup_apartment: order.pickup_apartment,
      pickup_postal_code: order.pickup_postal_code,
      delivery_street: order.delivery_street,
      delivery_building_number: order.delivery_building_number,
      delivery_apartment: order.delivery_apartment,
      delivery_postal_code: order.delivery_postal_code,
      preferred_date: order.preferred_date,
      preferred_time: order.preferred_time,
      pickup_floor: order.pickup_floor,
      delivery_floor: order.delivery_floor,
      pickup_has_elevator: order.pickup_has_elevator,
      delivery_has_elevator: order.delivery_has_elevator,
      notes: order.notes,
      original_message: order.original_message,
      customer_email: order.customer_email,
      customer_phone: order.customer_phone,
      status: nextStatus,
    };

    try {
      const updatedOrder = await fetchJson<OrderRecord>(`/api/v1/orders/${order.id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
        headers: { 'Content-Type': 'application/json' },
      });
      setOrders((current) =>
        current.map((currentOrder) => (currentOrder.id === updatedOrder.id ? updatedOrder : currentOrder)),
      );
      setOrderListSuccess(
        nextStatus === 'approved'
          ? `Zlecenie #${order.id} zostało zatwierdzone.`
          : `Rozpoczęto weryfikację zlecenia #${order.id}.`,
      );
    } catch (error) {
      setOrderListError(
        error instanceof Error ? error.message : 'Nie udało się zmienić statusu zlecenia.',
      );
    } finally {
      setIsUpdatingOrderId(null);
    }
  };

  const deleteOrder = async (orderId: number) => {
    const confirmed = window.confirm('Czy na pewno chcesz usunąć to zlecenie?');
    if (!confirmed) return;

    try {
      await fetchJson(`/api/v1/orders/${orderId}`, { method: 'DELETE' });
      setOrders((current) => current.filter((order) => order.id !== orderId));
      if (form.id === orderId) resetForm();
      setSuccessMessage('Zlecenie zostało usunięte.');
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Nie udało się usunąć zlecenia.');
    }
  };

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-sky-700">
              <ShieldCheck className="h-3.5 w-3.5" />
              Panel pracownika
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">Obsługa zgłoszeń</h1>
            <p className="mt-2 text-sm text-slate-600">
              Weryfikuj dane klientów, obsługuj wiadomości i przygotowuj zlecenia do zatwierdzenia.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-sm">
            <span className="rounded-xl bg-slate-100 px-3 py-2 text-slate-700">{orders.length} zleceń</span>
            <span className="rounded-xl bg-slate-100 px-3 py-2 text-slate-700">{vehicles.length} pojazdów</span>
            <span className="rounded-xl bg-slate-100 px-3 py-2 text-slate-700">
              {incomingEmails.filter((email) => email.status !== 'converted').length} oczekujących e-maili
            </span>
          </div>
        </div>
      </section>

      <button
        type="button"
        aria-expanded={isManualFormOpen}
        aria-controls="order-form"
        onClick={() => {
          if (!isManualFormOpen) {
            setSubmitError(null);
            setSuccessMessage(null);
          }
          setIsManualFormOpen((current) => !current);
        }}
        className="flex w-full items-center justify-between rounded-2xl border border-dashed border-sky-300 bg-sky-50 p-5 text-left transition hover:border-sky-400 hover:bg-sky-100"
      >
        <span>
          <span className="block font-semibold text-slate-900">Dodaj zlecenie ręcznie</span>
          <span className="mt-1 block text-sm text-slate-600">
            {isManualFormOpen ? 'Formularz jest rozwinięty.' : 'Rozwiń formularz i wprowadź dane nowego zgłoszenia.'}
          </span>
        </span>
        <Plus className={`h-5 w-5 text-sky-700 transition-transform ${isManualFormOpen ? 'rotate-45' : ''}`} />
      </button>

      {isManualFormOpen ? (
      <section id="order-form" className="scroll-mt-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6 flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-slate-900">Zlecenie</h2>
          {form.id ? (
            <span className="rounded-full bg-indigo-100 px-2.5 py-1 text-xs font-medium text-indigo-700">
              Edycja zlecenia #{form.id}
            </span>
          ) : (
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
              Nowe zlecenie
            </span>
          )}
        </div>

        <div className="grid gap-5 md:grid-cols-2">
          <label className="md:col-span-2">
            <span className="mb-2 block text-sm font-medium text-slate-700">Opis ładunku</span>
            <input
              value={form.cargo_description}
              onChange={(event) => updateField('cargo_description', event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <label>
            <span className="mb-2 block text-sm font-medium text-slate-700">Długość (cm)</span>
            <input
              type="number"
              min="0"
              step="0.1"
              value={form.length_cm}
              onChange={(event) => updateField('length_cm', event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <label>
            <span className="mb-2 block text-sm font-medium text-slate-700">Szerokość (cm)</span>
            <input
              type="number"
              min="0"
              step="0.1"
              value={form.width_cm}
              onChange={(event) => updateField('width_cm', event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <label>
            <span className="mb-2 block text-sm font-medium text-slate-700">Wysokość (cm)</span>
            <input
              type="number"
              min="0"
              step="0.1"
              value={form.height_cm}
              onChange={(event) => updateField('height_cm', event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <label>
            <span className="mb-2 block text-sm font-medium text-slate-700">Waga (kg)</span>
            <input
              type="number"
              min="0"
              step="0.1"
              value={form.weight_kg}
              onChange={(event) => updateField('weight_kg', event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <label>
            <span className="mb-2 block text-sm font-medium text-slate-700">Ilość sztuk</span>
            <input
              type="number"
              min="1"
              value={form.quantity}
              onChange={(event) => updateField('quantity', Number(event.target.value || 1))}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <AddressFields
            title="Adres odbioru"
            values={{
              street: form.pickup_street,
              buildingNumber: form.pickup_building_number,
              apartment: form.pickup_apartment,
              postalCode: form.pickup_postal_code,
              city: form.pickup_location,
            }}
            onChange={(field, value) => {
              const keys = {
                street: 'pickup_street',
                buildingNumber: 'pickup_building_number',
                apartment: 'pickup_apartment',
                postalCode: 'pickup_postal_code',
                city: 'pickup_location',
              } as const;
              updateField(keys[field], value);
            }}
          />

          <AddressFields
            title="Adres dostawy"
            values={{
              street: form.delivery_street,
              buildingNumber: form.delivery_building_number,
              apartment: form.delivery_apartment,
              postalCode: form.delivery_postal_code,
              city: form.delivery_location,
            }}
            onChange={(field, value) => {
              const keys = {
                street: 'delivery_street',
                buildingNumber: 'delivery_building_number',
                apartment: 'delivery_apartment',
                postalCode: 'delivery_postal_code',
                city: 'delivery_location',
              } as const;
              updateField(keys[field], value);
            }}
          />

          <label>
            <span className="mb-2 block text-sm font-medium text-slate-700">E-mail klienta</span>
            <input
              type="email"
              maxLength={254}
              value={form.customer_email}
              onChange={(event) => updateField('customer_email', event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <label>
            <span className="mb-2 block text-sm font-medium text-slate-700">Telefon klienta (opcjonalnie)</span>
            <input
              type="tel"
              maxLength={32}
              value={form.customer_phone}
              onChange={(event) => updateField('customer_phone', event.target.value)}
              placeholder="+48 600 700 800"
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <label>
            <span className="mb-2 block text-sm font-medium text-slate-700">Preferowana data</span>
            <input
              type="date"
              value={form.preferred_date}
              onChange={(event) => updateField('preferred_date', event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <label>
            <span className="mb-2 block text-sm font-medium text-slate-700">Preferowany czas</span>
            <input
              type="time"
              value={form.preferred_time}
              onChange={(event) => updateField('preferred_time', event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <label>
            <span className="mb-2 block text-sm font-medium text-slate-700">Piętro odbioru</span>
            <input
              type="number"
              min="-5"
              max="100"
              value={form.pickup_floor}
              onChange={(event) => updateField('pickup_floor', event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <label>
            <span className="mb-2 block text-sm font-medium text-slate-700">Piętro dostawy</span>
            <input
              type="number"
              min="-5"
              max="100"
              value={form.delivery_floor}
              onChange={(event) => updateField('delivery_floor', event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={Boolean(form.pickup_has_elevator)}
              onChange={(event) => updateField('pickup_has_elevator', event.target.checked)}
            />
            Odbiór z windą
          </label>

          <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={Boolean(form.delivery_has_elevator)}
              onChange={(event) => updateField('delivery_has_elevator', event.target.checked)}
            />
            Dostawa z windą
          </label>

          <label className="md:col-span-2">
            <span className="mb-2 block text-sm font-medium text-slate-700">Uwagi</span>
            <textarea
              rows={3}
              value={form.notes}
              onChange={(event) => updateField('notes', event.target.value)}
              className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <label className="md:col-span-2">
            <span className="mb-2 block text-sm font-medium text-slate-700">Oryginalna wiadomość klienta</span>
            <textarea
              rows={5}
              maxLength={3000}
              value={form.original_message}
              onChange={(event) => updateField('original_message', event.target.value)}
              className="w-full resize-y rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </label>

          <label className="md:col-span-2">
            <span className="mb-2 block text-sm font-medium text-slate-700">Status</span>
            <select
              value={form.status}
              onChange={(event) => updateField('status', event.target.value as OrderStatus)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            >
              <option value="new">Nowe</option>
              <option value="in_review">W trakcie weryfikacji</option>
              <option value="approved">Zatwierdzone</option>
            </select>
          </label>
        </div>

        {(submitError || successMessage) && (
          <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm">
            {submitError ? <p className="text-rose-700">{submitError}</p> : <p className="text-emerald-700">{successMessage}</p>}
          </div>
        )}

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={saveOrder}
            disabled={isSaving}
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            {form.id ? 'Zapisz zmiany' : 'Utwórz zlecenie'}
          </button>

          <button
            type="button"
            onClick={() => setIsManualFormOpen(false)}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            <RefreshCw className="h-4 w-4" />
            Zwiń formularz
          </button>
        </div>
      </section>
      ) : null}

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-5 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Skrzynka zgłoszeń e-mail</h2>
            <p className="mt-1 text-sm text-slate-500">
              Wiadomości są analizowane przez AI, ale każde zlecenie wymaga sprawdzenia przez pracownika.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-medium text-amber-800">
              {incomingEmails.length} wiadomości
            </span>
            <button
              type="button"
              onClick={() => void syncIncomingEmails()}
              disabled={isSyncingEmails}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${isSyncingEmails ? 'animate-spin' : ''}`} />
              {isSyncingEmails ? 'Sprawdzam...' : 'Sprawdź pocztę'}
            </button>
          </div>
        </div>

        <div className="mb-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <label className="flex items-center gap-3 text-sm font-medium text-slate-800">
            <input
              type="checkbox"
              checked={emailFilterEnabled}
              onChange={(event) => setEmailFilterEnabled(event.target.checked)}
            />
            Pobieraj tylko wiadomości z frazą w temacie
          </label>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <label className="min-w-60 flex-1">
              <span className="mb-1 block text-sm text-slate-600">Fraza w temacie (Subject)</span>
              <input
                maxLength={200}
                value={emailFilterPhrase}
                onChange={(event) => setEmailFilterPhrase(event.target.value)}
                placeholder="np. CargoBrief"
                disabled={!emailFilterEnabled}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 disabled:bg-slate-100"
              />
            </label>
            <button
              type="button"
              onClick={() => void saveEmailInboxFilter()}
              disabled={
                isSavingEmailFilter ||
                (emailFilterEnabled && !emailFilterPhrase.trim())
              }
              className="rounded-xl bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSavingEmailFilter ? 'Zapisywanie...' : 'Zapisz filtr'}
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Dopasowanie nie uwzględnia wielkości liter. Ustawienie dotyczy automatycznego i ręcznego pobierania.
            Wiadomości bez dopasowania pozostają nieprzeczytane w skrzynce.
          </p>
        </div>

        {(emailActionError || emailActionSuccess) && (
          <div
            role={emailActionError ? 'alert' : 'status'}
            className={`mb-4 rounded-xl border p-3 text-sm ${
              emailActionError
                ? 'border-rose-200 bg-rose-50 text-rose-700'
                : 'border-emerald-200 bg-emerald-50 text-emerald-700'
            }`}
          >
            {emailActionError ?? emailActionSuccess}
          </div>
        )}

        {incomingEmails.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
            Brak nowych wiadomości. Ustaw Gmail IMAP w backendowym pliku .env, aby włączać odbiór.
          </div>
        ) : (
          <div className="space-y-4">
            {incomingEmails.map((incomingEmail) => (
              <article key={incomingEmail.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-slate-900">
                        {incomingEmail.subject || '(bez tematu)'}
                      </h3>
                      <span className={`rounded-full px-2 py-1 text-xs font-medium ${
                        incomingEmail.status === 'converted'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {incomingEmail.status === 'converted'
                          ? 'Dodano do kolejki'
                          : incomingEmail.status === 'ready'
                            ? 'Analiza gotowa'
                            : 'Oczekuje na analizę'}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-600">
                      {incomingEmail.sender_email ?? 'Nie rozpoznano adresu nadawcy'}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {incomingEmail.status === 'converted' && incomingEmail.converted_order_id ? (
                      <button
                        type="button"
                        onClick={() => void scrollToOrder(incomingEmail.converted_order_id!)}
                        className="rounded-xl bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700"
                      >
                        Przejdź do zlecenia #{incomingEmail.converted_order_id}
                      </button>
                    ) : incomingEmail.status !== 'converted' ? (
                      <button
                        type="button"
                        onClick={() => analyzeIncomingEmail(incomingEmail.id)}
                        disabled={isAnalyzingEmailId !== null}
                        className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                      >
                        {isAnalyzingEmailId === incomingEmail.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <RefreshCw className="h-4 w-4" />
                        )}
                        Analizuj i dodaj do kolejki
                      </button>
                    ) : null}
                  </div>
                </div>

                {incomingEmail.analysis ? (
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    {incomingEmail.analysis.missing_fields.length > 0 ? (
                      <span className="rounded-lg bg-amber-100 px-2 py-1 text-amber-900">
                        Braki: {incomingEmail.analysis.missing_fields.join(', ')}
                      </span>
                    ) : (
                      <span className="rounded-lg bg-emerald-100 px-2 py-1 text-emerald-800">
                        AI nie wykryło brakujących pól
                      </span>
                    )}
                    {incomingEmail.analysis.ambiguities.map((ambiguity, index) => (
                      <span key={`${index}-${ambiguity}`} className="rounded-lg bg-rose-100 px-2 py-1 text-rose-800">
                        Niepewność: {ambiguity}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="mt-3 text-xs text-amber-800">
                    {incomingEmail.status === 'converted'
                      ? 'Wiadomość została już dodana do kolejki.'
                      : 'Szkic oczekuje na skonfigurowanie Gemini lub ręczne uzupełnienie.'}
                  </p>
                )}

                <details className="mt-3 rounded-xl border border-slate-200 bg-white px-3 py-2">
                  <summary className="cursor-pointer text-sm font-medium text-slate-700">
                    Treść wiadomości
                  </summary>
                  <p className="mt-2 max-h-48 overflow-y-auto whitespace-pre-wrap text-sm text-slate-600">
                    {incomingEmail.body}
                  </p>
                </details>
              </article>
            ))}
          </div>
        )}
      </section>

      <section id="review-queue" className="scroll-mt-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Kolejka do weryfikacji</h2>
            <p className="mt-1 text-sm text-slate-500">
              Sprawdź dane zlecenia i wiadomość klienta przed zatwierdzeniem.
            </p>
          </div>
          <div className="inline-flex items-center gap-2 text-sm text-slate-500">
            <MapPin className="h-4 w-4" />
            {isLoadingOrders ? 'Ładowanie...' : `${orders.length} zleceń`}
          </div>
        </div>

        <div className="mb-5 flex flex-wrap gap-2" aria-label="Filtruj zlecenia według statusu">
          {(['all', 'new', 'in_review', 'approved'] as const).map((filter) => {
            const count =
              filter === 'all' ? orders.length : orders.filter((order) => order.status === filter).length;
            const label = filter === 'all' ? 'Wszystkie' : statusLabels[filter];

            return (
              <button
                key={filter}
                type="button"
                aria-pressed={orderStatusFilter === filter}
                onClick={() => setOrderStatusFilter(filter)}
                className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${
                  orderStatusFilter === filter
                    ? 'bg-sky-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {label} <span className="ml-1 opacity-75">{count}</span>
              </button>
            );
          })}
        </div>

        <label className="mb-5 block">
          <span className="sr-only">Szukaj w kolejce zleceń</span>
          <span className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={orderSearch}
              onChange={(event) => setOrderSearch(event.target.value)}
              placeholder="Szukaj po ładunku, adresie, e-mailu, telefonie lub treści wiadomości..."
              className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-3 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </span>
        </label>

        {(orderListError || orderListSuccess) && (
          <div
            role={orderListError ? 'alert' : 'status'}
            className={`mb-4 rounded-xl border p-3 text-sm ${
              orderListError
                ? 'border-rose-200 bg-rose-50 text-rose-700'
                : 'border-emerald-200 bg-emerald-50 text-emerald-700'
            }`}
          >
            {orderListError ?? orderListSuccess}
          </div>
        )}

        {orders.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
            Brak zleceń do wyświetlenia. Utwórz pierwsze zlecenie, aby rozpocząć pracę.
          </div>
        ) : filteredOrders.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
            {orderSearch.trim()
              ? 'Nie znaleziono zleceń pasujących do wyszukiwania.'
              : 'Brak zleceń o wybranym statusie.'}
          </div>
        ) : (
          <div className="space-y-4">
            {filteredOrders.map((order) => (
              inlineEditingOrderId === order.id && inlineForm ? (
                <div
                  key={order.id}
                  id={`order-${order.id}`}
                  className={`rounded-2xl border p-4 transition ${
                    highlightedOrderId === order.id
                      ? 'border-sky-400 bg-sky-50 ring-2 ring-sky-200'
                      : 'border-sky-200 bg-sky-50'
                  }`}
                >
                  <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                    <h3 className="text-lg font-semibold text-slate-900">
                      Edycja zlecenia #{order.id}
                    </h3>
                    <span className="text-sm text-slate-600">
                      E-mail klienta jest tylko do odczytu.
                    </span>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    <label className="sm:col-span-2 lg:col-span-3">
                      <span className="mb-1 block text-sm font-medium text-slate-700">Opis ładunku</span>
                      <input
                        value={inlineForm.cargo_description}
                        onChange={(event) => updateInlineField('cargo_description', event.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                      />
                    </label>
                    {([
                      ['length_cm', 'Długość (cm)'],
                      ['width_cm', 'Szerokość (cm)'],
                      ['height_cm', 'Wysokość (cm)'],
                      ['weight_kg', 'Waga (kg)'],
                    ] as const).map(([field, label]) => (
                      <label key={field}>
                        <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>
                        <input
                          type="number"
                          min="0"
                          step="0.1"
                          value={inlineForm[field]}
                          onChange={(event) => updateInlineField(field, event.target.value)}
                          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                        />
                      </label>
                    ))}
                    <label>
                      <span className="mb-1 block text-sm font-medium text-slate-700">Ilość sztuk</span>
                      <input
                        type="number"
                        min="1"
                        value={inlineForm.quantity}
                        onChange={(event) => updateInlineField('quantity', Number(event.target.value || 1))}
                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                      />
                    </label>
                    <AddressFields
                      className="sm:col-span-2 lg:col-span-3"
                      title="Adres odbioru"
                      values={{
                        street: inlineForm.pickup_street,
                        buildingNumber: inlineForm.pickup_building_number,
                        apartment: inlineForm.pickup_apartment,
                        postalCode: inlineForm.pickup_postal_code,
                        city: inlineForm.pickup_location,
                      }}
                      onChange={(field, value) => {
                        const keys = {
                          street: 'pickup_street',
                          buildingNumber: 'pickup_building_number',
                          apartment: 'pickup_apartment',
                          postalCode: 'pickup_postal_code',
                          city: 'pickup_location',
                        } as const;
                        updateInlineField(keys[field], value);
                      }}
                    />
                    <AddressFields
                      className="sm:col-span-2 lg:col-span-3"
                      title="Adres dostawy"
                      values={{
                        street: inlineForm.delivery_street,
                        buildingNumber: inlineForm.delivery_building_number,
                        apartment: inlineForm.delivery_apartment,
                        postalCode: inlineForm.delivery_postal_code,
                        city: inlineForm.delivery_location,
                      }}
                      onChange={(field, value) => {
                        const keys = {
                          street: 'delivery_street',
                          buildingNumber: 'delivery_building_number',
                          apartment: 'delivery_apartment',
                          postalCode: 'delivery_postal_code',
                          city: 'delivery_location',
                        } as const;
                        updateInlineField(keys[field], value);
                      }}
                    />
                    <div>
                      <span className="mb-1 block text-sm font-medium text-slate-700">E-mail klienta</span>
                      <div className="flex gap-2">
                        <input
                          readOnly
                          aria-label="E-mail klienta (tylko do odczytu)"
                          value={order.customer_email ?? ''}
                          placeholder="brak adresu"
                          className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-slate-100 px-3 py-2 text-sm text-slate-600"
                        />
                        {order.customer_email ? (
                          <button
                            type="button"
                            onClick={() => void copyCustomerEmail(order.customer_email!)}
                            aria-label="Kopiuj e-mail klienta"
                            title="Kopiuj e-mail"
                            className="rounded-xl border border-slate-200 bg-white px-3 text-slate-700 hover:bg-slate-100"
                          >
                            <Clipboard className="h-4 w-4" />
                          </button>
                        ) : null}
                      </div>
                      {copyError ? <p role="alert" className="mt-1 text-xs text-rose-700">{copyError}</p> : null}
                    </div>
                    <label>
                      <span className="mb-1 block text-sm font-medium text-slate-700">Telefon klienta (opcjonalnie)</span>
                      <input
                        type="tel"
                        maxLength={32}
                        value={inlineForm.customer_phone}
                        onChange={(event) => updateInlineField('customer_phone', event.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                      />
                    </label>
                    <label>
                      <span className="mb-1 block text-sm font-medium text-slate-700">Preferowana data</span>
                      <input
                        type="date"
                        value={inlineForm.preferred_date}
                        onChange={(event) => updateInlineField('preferred_date', event.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                      />
                    </label>
                    <label>
                      <span className="mb-1 block text-sm font-medium text-slate-700">Preferowany czas</span>
                      <input
                        type="time"
                        value={inlineForm.preferred_time}
                        onChange={(event) => updateInlineField('preferred_time', event.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                      />
                    </label>
                    <label>
                      <span className="mb-1 block text-sm font-medium text-slate-700">Piętro odbioru</span>
                      <input
                        type="number"
                        min="-5"
                        max="100"
                        value={inlineForm.pickup_floor}
                        onChange={(event) => updateInlineField('pickup_floor', event.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                      />
                    </label>
                    <label>
                      <span className="mb-1 block text-sm font-medium text-slate-700">Piętro dostawy</span>
                      <input
                        type="number"
                        min="-5"
                        max="100"
                        value={inlineForm.delivery_floor}
                        onChange={(event) => updateInlineField('delivery_floor', event.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                      />
                    </label>
                    <label>
                      <span className="mb-1 block text-sm font-medium text-slate-700">Status</span>
                      <select
                        value={inlineForm.status}
                        onChange={(event) => updateInlineField('status', event.target.value as OrderStatus)}
                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                      >
                        <option value="new">Nowe</option>
                        <option value="in_review">W trakcie weryfikacji</option>
                        <option value="approved">Zatwierdzone</option>
                      </select>
                    </label>
                    <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={Boolean(inlineForm.pickup_has_elevator)}
                        onChange={(event) => updateInlineField('pickup_has_elevator', event.target.checked)}
                      />
                      Odbiór z windą
                    </label>
                    <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={Boolean(inlineForm.delivery_has_elevator)}
                        onChange={(event) => updateInlineField('delivery_has_elevator', event.target.checked)}
                      />
                      Dostawa z windą
                    </label>
                    <label className="sm:col-span-2 lg:col-span-3">
                      <span className="mb-1 block text-sm font-medium text-slate-700">Uwagi</span>
                      <textarea
                        rows={3}
                        value={inlineForm.notes}
                        onChange={(event) => updateInlineField('notes', event.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                      />
                    </label>
                    <label className="sm:col-span-2 lg:col-span-3">
                      <span className="mb-1 block text-sm font-medium text-slate-700">Oryginalna wiadomość klienta</span>
                      <textarea
                        rows={5}
                        maxLength={3000}
                        value={inlineForm.original_message}
                        onChange={(event) => updateInlineField('original_message', event.target.value)}
                        className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                      />
                    </label>
                  </div>
                  <div className="mt-5 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => void saveInlineEdit(order)}
                      disabled={isUpdatingOrderId !== null}
                      className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                    >
                      {isUpdatingOrderId === order.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                      Zapisz
                    </button>
                    <button
                      type="button"
                      onClick={cancelInlineEdit}
                      disabled={isUpdatingOrderId !== null}
                      className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                    >
                      Anuluj
                    </button>
                  </div>
                </div>
              ) : (
              <div
                key={order.id}
                id={`order-${order.id}`}
                className={`rounded-2xl border p-4 transition ${
                  highlightedOrderId === order.id
                    ? 'border-sky-400 bg-sky-50 ring-2 ring-sky-200'
                    : 'border-slate-200 bg-slate-50'
                }`}
              >
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-lg font-semibold text-slate-900">
                        {order.cargo_description || 'Zlecenie z e-maila — uzupełnij dane'}
                      </span>
                      <span className="rounded-full bg-sky-100 px-2 py-1 text-xs font-medium text-sky-700">
                        {statusLabels[order.status]}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-600">
                      {formatOrderAddress(order, 'pickup') || 'Brak danych odbioru'}
                      <ArrowRight className="mx-1 inline h-3.5 w-3.5" />
                      {formatOrderAddress(order, 'delivery') || 'Brak danych dostawy'}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {order.status !== 'approved' ? (
                      <button
                        type="button"
                        onClick={() => updateOrderStatus(order, 'approved')}
                        disabled={
                          isUpdatingOrderId !== null ||
                          !order.cargo_description?.trim() ||
                          !order.pickup_location?.trim() ||
                          !order.delivery_location?.trim()
                        }
                        title={
                          !order.cargo_description?.trim() ||
                          !order.pickup_location?.trim() ||
                          !order.delivery_location?.trim()
                            ? 'Uzupełnij opis ładunku oraz miejscowości odbioru i dostawy.'
                            : undefined
                        }
                        className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {isUpdatingOrderId === order.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <CheckCircle2 className="h-4 w-4" />
                        )}
                        Zatwierdź
                      </button>
                    ) : null}
                    <button
                      type="button"
                      onClick={() => startInlineEdit(order)}
                      className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                    >
                      <PencilLine className="h-4 w-4" />
                      Edytuj
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteOrder(order.id)}
                      className="inline-flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-100"
                    >
                      <Trash2 className="h-4 w-4" />
                      Usuń
                    </button>
                  </div>
                </div>

                <div className="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-4">
                  <div>Wymiary: {order.length_cm || '-'} × {order.width_cm || '-'} × {order.height_cm || '-'} cm</div>
                  <div>Waga: {order.weight_kg ? `${order.weight_kg} kg` : '—'}</div>
                  <div>Ilość: {order.quantity}</div>
                  <div>Data: {order.preferred_date || '—'}</div>
                </div>
                {!order.cargo_description?.trim() ||
                !order.pickup_location?.trim() ||
                !order.delivery_location?.trim() ? (
                  <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                    Uzupełnij opis ładunku oraz miejscowości odbioru i dostawy przed zatwierdzeniem.
                  </p>
                ) : null}
                <div className="mt-3 flex items-center gap-2 text-sm text-slate-600">
                  <span>E-mail klienta: {order.customer_email || 'brak adresu'}</span>
                  {order.customer_email ? (
                    <button
                      type="button"
                      onClick={() => void copyCustomerEmail(order.customer_email!)}
                      aria-label="Kopiuj e-mail klienta"
                      title="Kopiuj e-mail"
                      className="rounded p-1 text-slate-500 hover:bg-white hover:text-slate-900"
                    >
                      <Clipboard className="h-4 w-4" />
                    </button>
                  ) : null}
                </div>
                <div className="mt-1 text-sm text-slate-600">
                  Telefon klienta: {order.customer_phone || 'brak numeru'}
                </div>

                <div className="mt-3 rounded-xl bg-white px-3 py-2 text-sm">
                  <span className="font-medium text-slate-700">Dopasowanie pojazdu: </span>
                  <span className="text-slate-600">
                    {order.match.status === 'confirmed' && order.match.recommended_vehicle
                      ? order.match.recommended_vehicle.name
                      : order.match.message}
                  </span>
                </div>

                {order.original_message ? (
                  <details className="mt-3 rounded-xl border border-slate-200 bg-white px-3 py-2">
                    <summary className="cursor-pointer text-sm font-medium text-slate-700">
                      Oryginalna wiadomość klienta
                    </summary>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">{order.original_message}</p>
                  </details>
                ) : null}
              </div>
              )
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

type AddressField = 'street' | 'buildingNumber' | 'apartment' | 'postalCode' | 'city';

type AddressValues = Record<AddressField, string>;

function AddressFields({
  className,
  title,
  values,
  onChange,
}: {
  className?: string;
  title: string;
  values: AddressValues;
  onChange: (field: AddressField, value: string) => void;
}) {
  const fields: { key: AddressField; label: string; placeholder?: string }[] = [
    { key: 'street', label: 'Ulica' },
    { key: 'buildingNumber', label: 'Nr budynku' },
    { key: 'apartment', label: 'Nr lokalu (opcjonalnie)' },
    { key: 'postalCode', label: 'Kod pocztowy' },
    { key: 'city', label: 'Miejscowość' },
  ];

  return (
    <fieldset className={`grid grid-cols-2 gap-3 sm:grid-cols-3 ${className ?? ''}`}>
      <legend className="mb-1 text-sm font-semibold text-slate-800">{title}</legend>
      {fields.map((field) => (
        <label key={field.key}>
          <span className="mb-1 block text-xs font-medium text-slate-600">{field.label}</span>
          <input
            value={values[field.key]}
            onChange={(event) => onChange(field.key, event.target.value)}
            placeholder={field.placeholder}
            maxLength={
              field.key === 'street' || field.key === 'city'
                ? 255
                : field.key === 'postalCode'
                  ? 20
                  : 30
            }
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-sky-300 focus:ring-2 focus:ring-sky-100"
          />
        </label>
      ))}
    </fieldset>
  );
}

export default App;
