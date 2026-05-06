"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft, ChevronRight, Plus, Trash2, ShoppingCart, CreditCard, X,
} from "lucide-react";
import api from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/formatters";
import NumberInput from "@/components/ui/NumberInput";

// ── Types ────────────────────────────────────────────────────

interface UnsoldApartment {
  id: number;
  label: string;
  building_number: string;
  floor: string | null;
  unit_number: string | null;
  room_count: number | null;
  net_area_sqm: number | null;
  list_price_with_vat: number | null;
  list_price_no_vat: number | null;
}

interface Sale {
  id: number;
  apartment_id: number;
  buyer_name: string;
  buyer_id_number: string | null;
  contract_date: string;
  original_price_with_vat: number | null;
  final_price_with_vat: number;
  final_price_no_vat: number;
  is_recognized_by_bank: boolean;
  is_non_linear: boolean;
  notes: string | null;
}

interface Payment {
  id: number;
  contract_id: number;
  payment_number: number;
  description: string | null;
  scheduled_amount: number;
  scheduled_date: string;
  actual_amount: number | null;
  actual_date: string | null;
  status: string;
  reference_number: string | null;
  notes: string | null;
}

interface SalesSummary {
  total_units_developer: number;
  total_sold: number;
  sold_percent: number;
  recognized_by_bank: number;
  recognized_percent: number;
  unsold: number;
}

// ── Main Component ───────────────────────────────────────────

export default function SalesStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [paymentSaleId, setPaymentSaleId] = useState<number | null>(null);

  // Queries
  const { data: summary } = useQuery<SalesSummary>({
    queryKey: ["sales-summary", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/sales/summary`)).data,
  });

  // VAT rate from the current monthly report (e.g. 0.18 = 18%).
  const { data: report } = useQuery<{ vat_rate: number }>({
    queryKey: ["report", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}`)).data,
  });
  const vatRate = Number(report?.vat_rate) || 0.18;

  const { data: sales = [] } = useQuery<Sale[]>({
    queryKey: ["sales", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/sales`)).data,
  });

  const { data: unsold = [] } = useQuery<UnsoldApartment[]>({
    queryKey: ["unsold-apartments", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/apartments/unsold`)).data,
  });

  const deleteMutation = useMutation({
    mutationFn: (saleId: number) => api.delete(`/projects/${projectId}/sales/${saleId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sales", projectId] });
      qc.invalidateQueries({ queryKey: ["sales-summary", projectId] });
      qc.invalidateQueries({ queryKey: ["unsold-apartments", projectId] });
      qc.invalidateQueries({ queryKey: ["completeness", reportId] });
    },
  });

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label='סה"כ יח"ד יזם' value={String(summary.total_units_developer)} />
          <StatCard label="נמכרו" value={String(summary.total_sold)} sub={`${summary.sold_percent}%`} />
          <StatCard label="מוכרות (>15%)" value={String(summary.recognized_by_bank)} sub={`${summary.recognized_percent}%`} />
          <StatCard label="למכירה" value={String(summary.unsold)} />
        </div>
      )}

      {/* Sales list */}
      <div className="bg-white rounded-2xl border border-gray-200">
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <h2 className="text-lg font-bold text-gray-900">רשימת מכירות</h2>
          <button
            onClick={() => setShowForm(true)}
            disabled={unsold.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-xl text-sm font-medium hover:bg-primary-dark transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Plus size={16} /> הוסף מכירה
          </button>
        </div>

        {sales.length === 0 ? (
          <div className="text-center py-12">
            <ShoppingCart size={40} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500">טרם הוזנו מכירות</p>
            <p className="text-gray-400 text-sm mt-1">לחץ &quot;הוסף מכירה&quot; להתחיל</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-500 bg-gray-50 border-b">
                  <th className="text-right px-4 py-3 font-medium">דירה</th>
                  <th className="text-right px-4 py-3 font-medium">קונה</th>
                  <th className="text-right px-4 py-3 font-medium">תאריך</th>
                  <th className="text-left px-4 py-3 font-medium">מחיר כולל מע&quot;מ</th>
                  <th className="text-left px-4 py-3 font-medium">מחיר ללא מע&quot;מ</th>
                  <th className="text-center px-4 py-3 font-medium">תשלומים</th>
                  <th className="text-center px-4 py-3 font-medium w-16"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {sales.map((sale) => (
                  <tr key={sale.id} className="hover:bg-gray-50/50 transition">
                    <td className="px-4 py-3 text-sm text-gray-900">דירה {sale.apartment_id}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{sale.buyer_name}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{formatDate(sale.contract_date)}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-left">{formatCurrency(sale.final_price_with_vat)}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 text-left">{formatCurrency(sale.final_price_no_vat)}</td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => setPaymentSaleId(sale.id)}
                        className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 rounded-lg text-xs font-medium hover:bg-blue-100 transition"
                      >
                        <CreditCard size={14} /> תשלומים
                      </button>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => { if (confirm("למחוק מכירה זו?")) deleteMutation.mutate(sale.id); }}
                        className="text-gray-400 hover:text-red-500 transition"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add sale form modal */}
      {showForm && (
        <SaleFormModal
          projectId={projectId}
          unsold={unsold}
          vatRate={vatRate}
          onClose={() => setShowForm(false)}
          onSuccess={() => {
            setShowForm(false);
            qc.invalidateQueries({ queryKey: ["sales", projectId] });
            qc.invalidateQueries({ queryKey: ["sales-summary", projectId] });
            qc.invalidateQueries({ queryKey: ["unsold-apartments", projectId] });
          }}
        />
      )}

      {/* Payment schedule modal */}
      {paymentSaleId !== null && (
        <PaymentScheduleModal
          projectId={projectId}
          saleId={paymentSaleId}
          sale={sales.find((s) => s.id === paymentSaleId)!}
          onClose={() => setPaymentSaleId(null)}
        />
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/bank-statement`)}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition"
        >
          <ChevronRight size={18} /> חזרה לתדפיס בנק
        </button>
        <button
          onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/construction`)}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition"
        >
          המשך להתקדמות בנייה <ChevronLeft size={18} />
        </button>
      </div>
    </div>
  );
}

// ── Sale Form Modal ──────────────────────────────────────────

function SaleFormModal({
  projectId, unsold, onClose, onSuccess, vatRate,
}: {
  projectId: string;
  unsold: UnsoldApartment[];
  onClose: () => void;
  onSuccess: () => void;
  vatRate: number;
}) {
  const [aptId, setAptId] = useState("");
  const [buyerName, setBuyerName] = useState("");
  const [buyerId, setBuyerId] = useState("");
  const [contractDate, setContractDate] = useState("");
  const [priceWithVat, setPriceWithVat] = useState("");
  const [priceNoVat, setPriceNoVat] = useState("");
  // VAT rate captured at sale time. Pre-filled from the report's vat_rate
  // but the user can override per-sale before submission. Stored as the
  // fractional rate (0.18 for 18%).
  const [saleVatRate, setSaleVatRate] = useState<number>(vatRate);
  // Re-sync if the report query loads after the modal mounted.
  useEffect(() => { setSaleVatRate(vatRate); }, [vatRate]);
  const vatMultiplier = 1 + saleVatRate;
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const selectedApt = unsold.find((a) => a.id === Number(aptId));

  // Auto-fill prices from apartment list price
  const handleAptChange = (id: string) => {
    setAptId(id);
    const apt = unsold.find((a) => a.id === Number(id));
    if (apt) {
      if (apt.list_price_with_vat) setPriceWithVat(String(apt.list_price_with_vat));
      if (apt.list_price_no_vat) setPriceNoVat(String(apt.list_price_no_vat));
    }
  };

  // Auto-calc no-VAT from with-VAT, and vice versa, using the current
  // monthly report's VAT rate.
  const handlePriceWithVatChange = (val: string) => {
    setPriceWithVat(val);
    if (val && !isNaN(Number(val))) {
      setPriceNoVat(String(Math.round(Number(val) / vatMultiplier)));
    }
  };
  const handlePriceNoVatChange = (val: string) => {
    setPriceNoVat(val);
    if (val && !isNaN(Number(val))) {
      setPriceWithVat(String(Math.round(Number(val) * vatMultiplier)));
    }
  };

  const handleSubmit = async () => {
    // Specific validation messages so the user can see exactly which field
    // the form thinks is empty (was previously "fill all fields" with no hint).
    if (!aptId) { setError("יש לבחור דירה"); return; }
    if (!buyerName.trim()) { setError("יש למלא שם קונה"); return; }
    if (!contractDate) { setError("יש לבחור תאריך חוזה"); return; }
    if (!priceWithVat || Number(priceWithVat) <= 0) {
      setError('יש להזין מחיר חוזה כולל מע"מ'); return;
    }
    if (!priceNoVat || Number(priceNoVat) <= 0) {
      setError('יש להזין מחיר חוזה ללא מע"מ'); return;
    }
    setSaving(true);
    setError("");
    try {
      await api.post(`/projects/${projectId}/sales`, {
        apartment_id: Number(aptId),
        buyer_name: buyerName,
        buyer_id_number: buyerId || null,
        contract_date: contractDate,
        original_price_with_vat: selectedApt?.list_price_with_vat || Number(priceWithVat),
        final_price_with_vat: Number(priceWithVat),
        final_price_no_vat: Number(priceNoVat),
        vat_rate: saleVatRate,
      });
      onSuccess();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "שגיאה בשמירה");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-lg p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-gray-900">הוספת מכירה חדשה</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <div className="space-y-4">
          {/* Apartment select */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">דירה</label>
            <select
              value={aptId}
              onChange={(e) => handleAptChange(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm"
            >
              <option value="">— בחר דירה —</option>
              {unsold.map((a) => (
                <option key={a.id} value={a.id}>{a.label}</option>
              ))}
            </select>
            {selectedApt && (
              <p className="text-xs text-gray-400 mt-1">
                {selectedApt.room_count ? `${selectedApt.room_count} חד׳` : ""}
                {selectedApt.net_area_sqm ? ` | ${selectedApt.net_area_sqm} מ"ר` : ""}
                {selectedApt.list_price_with_vat ? ` | מחירון: ${formatCurrency(selectedApt.list_price_with_vat)}` : ""}
              </p>
            )}
          </div>

          {/* Buyer */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">שם קונה</label>
              <input
                value={buyerName}
                onChange={(e) => setBuyerName(e.target.value)}
                placeholder="ישראל ישראלי"
                className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">ת.ז.</label>
              <input
                value={buyerId}
                onChange={(e) => setBuyerId(e.target.value)}
                placeholder="אופציונלי"
                className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm"
              />
            </div>
          </div>

          {/* Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">תאריך חוזה</label>
            <input
              type="date"
              value={contractDate}
              onChange={(e) => setContractDate(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm"
            />
          </div>

          {/* Prices */}
          {selectedApt && selectedApt.list_price_with_vat && (
            <div className="bg-gray-50 rounded-xl p-3 flex items-center justify-between">
              <span className="text-sm text-gray-500">מחיר מחירון (מקורי)</span>
              <span className="text-sm font-bold text-gray-700">{formatCurrency(selectedApt.list_price_with_vat)}</span>
            </div>
          )}
          {/* VAT at sale time — pre-filled from monthly report. User can override per-sale. */}
          <div className="bg-gray-50 rounded-xl p-3 mb-3 border border-gray-100">
            <label className="block text-xs font-medium text-gray-700 mb-1.5">
              מע״מ במועד רכישת הדירה
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                step="0.5"
                value={String(saleVatRate * 100)}
                onChange={(e) => {
                  const pct = Number(e.target.value);
                  if (!isNaN(pct) && pct >= 0 && pct <= 100) {
                    const newRate = pct / 100;
                    setSaleVatRate(newRate);
                    // Re-derive no-VAT side from with-VAT to stay consistent.
                    if (priceWithVat && !isNaN(Number(priceWithVat))) {
                      setPriceNoVat(String(Math.round(Number(priceWithVat) / (1 + newRate))));
                    }
                  }
                }}
                dir="ltr"
                className="w-20 px-2 py-1.5 rounded-lg border border-gray-200 text-sm text-left focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
              <span className="text-sm text-gray-500">%</span>
              <span className="text-xs text-gray-400 mr-auto">
                ערך ברירת מחדל מהדוח החודשי. שנה במידה והשתנה במועד הרכישה.
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">מחיר חוזה כולל מע&quot;מ</label>
              <NumberInput
                value={priceWithVat}
                onChange={handlePriceWithVatChange}
                placeholder="₪"
                className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm text-left"
              />
              {selectedApt && selectedApt.list_price_with_vat && priceWithVat && (
                <p className={`text-xs mt-1 ${Number(priceWithVat) > selectedApt.list_price_with_vat ? "text-green-600" : Number(priceWithVat) < selectedApt.list_price_with_vat ? "text-red-600" : "text-gray-400"}`}>
                  {Number(priceWithVat) > selectedApt.list_price_with_vat
                    ? `+${formatCurrency(Number(priceWithVat) - selectedApt.list_price_with_vat)} מעל מחירון`
                    : Number(priceWithVat) < selectedApt.list_price_with_vat
                    ? `${formatCurrency(selectedApt.list_price_with_vat - Number(priceWithVat))} הנחה`
                    : "זהה למחירון"}
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">מחיר חוזה ללא מע&quot;מ</label>
              <NumberInput
                value={priceNoVat}
                onChange={handlePriceNoVatChange}
                placeholder="חישוב אוטומטי"
                className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm text-left"
              />
            </div>
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <button
            onClick={handleSubmit}
            disabled={saving}
            className="w-full py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition disabled:opacity-50"
          >
            {saving ? "שומר..." : "שמור מכירה"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Payment Schedule Modal ───────────────────────────────────

function PaymentScheduleModal({
  projectId, saleId, sale, onClose,
}: {
  projectId: string;
  saleId: number;
  sale: Sale;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [showAddRow, setShowAddRow] = useState(false);
  const [newAmount, setNewAmount] = useState("");
  const [newDate, setNewDate] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [usePercent, setUsePercent] = useState(false);

  const { data: payments = [], isLoading } = useQuery<Payment[]>({
    queryKey: ["payments", saleId],
    queryFn: async () => (await api.get(`/projects/${projectId}/sales/${saleId}/payments`)).data,
  });

  const createMutation = useMutation({
    mutationFn: (body: { scheduled_amount: number; scheduled_date: string; description: string | null }) =>
      api.post(`/projects/${projectId}/sales/${saleId}/payments`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["payments", saleId] });
      setShowAddRow(false);
      setNewAmount("");
      setNewDate("");
      setNewDesc("");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ paymentId, body }: { paymentId: number; body: Record<string, unknown> }) =>
      api.patch(`/projects/${projectId}/sales/${saleId}/payments/${paymentId}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["payments", saleId] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (paymentId: number) =>
      api.delete(`/projects/${projectId}/sales/${saleId}/payments/${paymentId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["payments", saleId] }),
  });

  const totalScheduled = payments.reduce((s, p) => s + Number(p.scheduled_amount), 0);
  const totalPaid = payments.reduce((s, p) => s + (p.actual_amount ? Number(p.actual_amount) : 0), 0);
  const remaining = sale.final_price_with_vat - totalScheduled;

  const STATUS_LABELS: Record<string, string> = {
    scheduled: "מתוכנן",
    paid: "שולם",
    partial: "חלקי",
    overdue: "באיחור",
  };

  const STATUS_COLORS: Record<string, string> = {
    scheduled: "bg-gray-100 text-gray-700",
    paid: "bg-green-100 text-green-700",
    partial: "bg-amber-100 text-amber-700",
    overdue: "bg-red-100 text-red-700",
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-gray-900">פריסת תשלומים</h3>
              <p className="text-sm text-gray-500 mt-1">
                {sale.buyer_name} | {formatCurrency(sale.final_price_with_vat)}
              </p>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <X size={20} />
            </button>
          </div>

          {/* Totals */}
          <div className="grid grid-cols-3 gap-3 mt-4">
            <div className="bg-gray-50 rounded-xl p-3 text-center">
              <p className="text-xs text-gray-500">סה&quot;כ מתוכנן</p>
              <p className="text-sm font-bold text-gray-900">{formatCurrency(totalScheduled)}</p>
            </div>
            <div className="bg-green-50 rounded-xl p-3 text-center">
              <p className="text-xs text-gray-500">שולם</p>
              <p className="text-sm font-bold text-green-700">{formatCurrency(totalPaid)}</p>
            </div>
            <div className={`rounded-xl p-3 text-center ${remaining > 0 ? "bg-amber-50" : "bg-green-50"}`}>
              <p className="text-xs text-gray-500">יתרה לפריסה</p>
              <p className={`text-sm font-bold ${remaining > 0 ? "text-amber-700" : "text-green-700"}`}>
                {formatCurrency(remaining)}
              </p>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-y-auto p-6">
          {payments.length === 0 && !showAddRow ? (
            <div className="text-center py-8">
              <CreditCard size={36} className="mx-auto text-gray-300 mb-3" />
              <p className="text-gray-500">טרם הוזנו תשלומים</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-500 border-b">
                  <th className="text-right pb-2 font-medium">#</th>
                  <th className="text-right pb-2 font-medium">תיאור</th>
                  <th className="text-left pb-2 font-medium">סכום</th>
                  <th className="text-right pb-2 font-medium">תאריך</th>
                  <th className="text-center pb-2 font-medium">סטטוס</th>
                  <th className="text-left pb-2 font-medium">שולם</th>
                  <th className="w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {payments.map((p) => (
                  <tr key={p.id} className="text-sm">
                    <td className="py-2.5 text-gray-500">{p.payment_number}</td>
                    <td className="py-2.5 text-gray-900">{p.description || "—"}</td>
                    <td className="py-2.5 text-left font-medium">
                      {formatCurrency(p.scheduled_amount)}
                      <span className="text-[10px] text-gray-400 mr-1">
                        ({(Number(p.scheduled_amount) / sale.final_price_with_vat * 100).toFixed(1)}%)
                      </span>
                    </td>
                    <td className="py-2.5 text-gray-600">{formatDate(p.scheduled_date)}</td>
                    <td className="py-2.5 text-center">
                      <select
                        value={p.status}
                        onChange={(e) => updateMutation.mutate({
                          paymentId: p.id,
                          body: {
                            status: e.target.value,
                            ...(e.target.value === "paid" ? {
                              actual_amount: Number(p.scheduled_amount),
                              actual_date: new Date().toISOString().split("T")[0],
                            } : {}),
                          },
                        })}
                        className={`px-2 py-1 rounded-lg text-xs font-medium border-0 ${STATUS_COLORS[p.status] || "bg-gray-100"}`}
                      >
                        {Object.entries(STATUS_LABELS).map(([val, label]) => (
                          <option key={val} value={val}>{label}</option>
                        ))}
                      </select>
                    </td>
                    <td className="py-2.5 text-left text-gray-600">
                      {p.actual_amount ? formatCurrency(Number(p.actual_amount)) : "—"}
                    </td>
                    <td className="py-2.5">
                      <button
                        onClick={() => deleteMutation.mutate(p.id)}
                        className="text-gray-400 hover:text-red-500 transition"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}

                {/* Add row */}
                {showAddRow && (
                  <tr className="text-sm bg-blue-50/30">
                    <td className="py-2.5 text-gray-400">—</td>
                    <td className="py-2.5">
                      <input
                        value={newDesc}
                        onChange={(e) => setNewDesc(e.target.value)}
                        placeholder="תיאור (לדוגמא: עם חתימת חוזה)"
                        className="w-full px-2 py-1 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-1 focus:ring-primary/20"
                      />
                    </td>
                    <td className="py-2.5">
                      <div className="flex items-center gap-1">
                        <NumberInput
                          value={newAmount}
                          onChange={setNewAmount}
                          placeholder={usePercent ? "%" : "₪"}
                          className="w-20 px-2 py-1 rounded-lg border border-gray-200 text-sm text-left focus:outline-none focus:ring-1 focus:ring-primary/20"
                        />
                        <button
                          onClick={() => setUsePercent(!usePercent)}
                          className={`px-1.5 py-1 rounded text-[10px] font-bold ${usePercent ? "bg-primary text-white" : "bg-gray-100 text-gray-500"}`}
                          title={usePercent ? "מצב אחוזים — לחץ למעבר לסכום" : "מצב סכום — לחץ למעבר לאחוזים"}
                        >
                          {usePercent ? "%" : "₪"}
                        </button>
                      </div>
                      {usePercent && newAmount && (
                        <p className="text-[10px] text-gray-400 mt-0.5" dir="ltr">
                          = {formatCurrency(Math.round(sale.final_price_with_vat * Number(newAmount) / 100))}
                        </p>
                      )}
                    </td>
                    <td className="py-2.5">
                      <input
                        type="date"
                        value={newDate}
                        onChange={(e) => setNewDate(e.target.value)}
                        className="px-2 py-1 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-1 focus:ring-primary/20"
                      />
                    </td>
                    <td className="py-2.5 text-center" colSpan={2}>
                      <button
                        onClick={() => {
                          if (!newAmount || !newDate) return;
                          const amount = usePercent
                            ? Math.round(sale.final_price_with_vat * Number(newAmount) / 100)
                            : Number(newAmount);
                          createMutation.mutate({
                            scheduled_amount: amount,
                            scheduled_date: newDate,
                            description: newDesc ? (usePercent ? `${newDesc} (${newAmount}%)` : newDesc) : null,
                          });
                        }}
                        disabled={createMutation.isPending}
                        className="px-3 py-1 bg-primary text-white rounded-lg text-xs font-medium hover:bg-primary-dark transition disabled:opacity-50"
                      >
                        {createMutation.isPending ? "..." : "שמור"}
                      </button>
                    </td>
                    <td className="py-2.5">
                      <button onClick={() => setShowAddRow(false)} className="text-gray-400 hover:text-gray-600">
                        <X size={14} />
                      </button>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-100">
          <button
            onClick={() => setShowAddRow(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-200 transition"
          >
            <Plus size={16} /> הוסף תשלום
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Stat Card ────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-4 text-center">
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
      {sub && <p className="text-xs text-primary font-medium mt-0.5">{sub}</p>}
    </div>
  );
}
