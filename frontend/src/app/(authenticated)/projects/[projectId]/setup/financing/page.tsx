"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Save, CheckCircle } from "lucide-react";
import api from "@/lib/api";
import NumberInput from "@/components/ui/NumberInput";

export default function FinancingSetupPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState({
    financing_type: "", credit_limit_total: "", credit_limit_construction: "",
    credit_limit_land: "", credit_limit_guarantees: "", equity_required_amount: "",
    equity_required_percent: "", presale_units_required: "", presale_amount_required: "",
    interest_rate: "", guarantee_fee_percent: "", notes: "",
  });

  const { data } = useQuery({
    queryKey: ["financing", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/setup/financing`)).data,
  });

  useEffect(() => {
    if (data) {
      setForm({
        financing_type: data.financing_type || "",
        credit_limit_total: data.credit_limit_total?.toString() || "",
        credit_limit_construction: data.credit_limit_construction?.toString() || "",
        credit_limit_land: data.credit_limit_land?.toString() || "",
        credit_limit_guarantees: data.credit_limit_guarantees?.toString() || "",
        equity_required_amount: data.equity_required_amount?.toString() || "",
        equity_required_percent: data.equity_required_percent?.toString() || "",
        presale_units_required: data.presale_units_required?.toString() || "",
        presale_amount_required: data.presale_amount_required?.toString() || "",
        interest_rate: data.interest_rate?.toString() || "",
        guarantee_fee_percent: data.guarantee_fee_percent?.toString() || "",
        notes: data.notes || "",
      });
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(form)) {
        if (value !== "") payload[key] = value;
      }
      return api.put(`/projects/${projectId}/setup/financing`, payload);
    },
    onSuccess: () => {
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      queryClient.invalidateQueries({ queryKey: ["setup-status", projectId] });
    },
  });

  const set = (field: string, value: string) => setForm((p) => ({ ...p, [field]: value }));

  return (
    <div className="max-w-2xl mx-auto">
      <button onClick={() => router.push(`/projects/${projectId}`)} className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4 transition">
        <ArrowRight size={18} /> חזרה לפרויקט
      </button>

      <h1 className="text-2xl font-bold text-gray-900 mb-2">תנאי מימון</h1>
      <p className="text-gray-500 mb-6">הסכם ליווי, מסגרות אשראי והון עצמי נדרש</p>

      <div className="bg-white rounded-2xl border border-gray-200 p-8 space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">סוג מימון</label>
          <select value={form.financing_type} onChange={(e) => set("financing_type", e.target.value)}
            className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary">
            <option value="">בחר...</option>
            <option value="banking">בנקאי</option>
            <option value="non_banking">חוץ בנקאי</option>
          </select>
        </div>

        <h3 className="font-bold text-gray-900 pt-2">מסגרות אשראי</h3>
        <div className="grid grid-cols-2 gap-4">
          <NumField label="מסגרת אשראי כוללת" value={form.credit_limit_total} onChange={(v) => set("credit_limit_total", v)} />
          <NumField label="מסגרת הקמה" value={form.credit_limit_construction} onChange={(v) => set("credit_limit_construction", v)} />
          <NumField label="מסגרת קרקע" value={form.credit_limit_land} onChange={(v) => set("credit_limit_land", v)} />
          <NumField label="מסגרת ערבויות" value={form.credit_limit_guarantees} onChange={(v) => set("credit_limit_guarantees", v)} />
        </div>

        <h3 className="font-bold text-gray-900 pt-2">הון עצמי ומכירות מוקדמות</h3>
        <div className="grid grid-cols-2 gap-4">
          <NumField label="הון עצמי נדרש (₪)" value={form.equity_required_amount} onChange={(v) => set("equity_required_amount", v)} />
          <NumField label="הון עצמי נדרש (%)" value={form.equity_required_percent} onChange={(v) => set("equity_required_percent", v)} />
          <NumField label="יחידות מכר מוקדם" value={form.presale_units_required} onChange={(v) => set("presale_units_required", v)} />
          <NumField label="סכום מכר מוקדם (₪)" value={form.presale_amount_required} onChange={(v) => set("presale_amount_required", v)} />
        </div>

        <h3 className="font-bold text-gray-900 pt-2">ריביות ועמלות</h3>
        <div className="grid grid-cols-2 gap-4">
          <NumField label="ריבית (%)" value={form.interest_rate} onChange={(v) => set("interest_rate", v)} />
          <NumField label="עמלת ערבות (%)" value={form.guarantee_fee_percent} onChange={(v) => set("guarantee_fee_percent", v)} />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">הערות</label>
          <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)} rows={3}
            className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary" />
        </div>

        <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
          className="w-full py-3 rounded-xl bg-primary text-white font-medium hover:bg-primary-dark transition disabled:opacity-50 flex items-center justify-center gap-2">
          {saved ? <><CheckCircle size={18} /> נשמר</> : mutation.isPending ? "שומר..." : <><Save size={18} /> שמור</>}
        </button>
      </div>
    </div>
  );
}

function NumField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      <NumberInput value={value} onChange={onChange}
        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary" />
    </div>
  );
}
