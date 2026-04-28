"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Save, CheckCircle } from "lucide-react";
import api from "@/lib/api";
import NumberInput from "@/components/ui/NumberInput";

export default function ContractorSetupPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState({
    contractor_name: "", contractor_company_number: "", contractor_classification: "",
    contract_amount_no_vat: "", contract_amount_with_vat: "",
    base_index_value: "", guarantee_percent: "", guarantee_amount: "",
    retention_percent: "", construction_duration_months: "", notes: "",
  });

  const { data } = useQuery({
    queryKey: ["contractor", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/setup/contractor`)).data,
  });

  useEffect(() => {
    if (data) {
      const f: Record<string, string> = {};
      for (const key of Object.keys(form)) {
        f[key] = data[key]?.toString() || "";
      }
      setForm(f as typeof form);
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(form)) {
        if (value !== "") payload[key] = value;
      }
      return api.put(`/projects/${projectId}/setup/contractor`, payload);
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

      <h1 className="text-2xl font-bold text-gray-900 mb-2">הסכם קבלן מבצע</h1>
      <p className="text-gray-500 mb-6">פרטי החוזה, תמורה, ערבויות ועיכבון</p>

      <div className="bg-white rounded-2xl border border-gray-200 p-8 space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <TxtField label="שם הקבלן" value={form.contractor_name} onChange={(v) => set("contractor_name", v)} />
          <TxtField label="ח.פ / ע.מ" value={form.contractor_company_number} onChange={(v) => set("contractor_company_number", v)} dir="ltr" />
        </div>
        <TxtField label="סיווג קבלני" value={form.contractor_classification} onChange={(v) => set("contractor_classification", v)} placeholder={"לדוגמה: ג'5 - ללא הגבלה"} />

        <h3 className="font-bold text-gray-900 pt-2">תמורה</h3>
        <div className="grid grid-cols-2 gap-4">
          <NumField label='תמורה ללא מע"מ (₪)' value={form.contract_amount_no_vat} onChange={(v) => set("contract_amount_no_vat", v)} />
          <NumField label='תמורה כולל מע"מ (₪)' value={form.contract_amount_with_vat} onChange={(v) => set("contract_amount_with_vat", v)} />
          <NumField label="מדד בסיס קבלן" value={form.base_index_value} onChange={(v) => set("base_index_value", v)} />
          <NumField label="משך בנייה (חודשים)" value={form.construction_duration_months} onChange={(v) => set("construction_duration_months", v)} />
        </div>

        <h3 className="font-bold text-gray-900 pt-2">ערבויות ועיכבון</h3>
        <div className="grid grid-cols-3 gap-4">
          <NumField label="ערבות ביצוע (%)" value={form.guarantee_percent} onChange={(v) => set("guarantee_percent", v)} />
          <NumField label="ערבות ביצוע (₪)" value={form.guarantee_amount} onChange={(v) => set("guarantee_amount", v)} />
          <NumField label="עיכבון (%)" value={form.retention_percent} onChange={(v) => set("retention_percent", v)} />
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

function TxtField({ label, value, onChange, placeholder, dir }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; dir?: string }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} dir={dir}
        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary" />
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
