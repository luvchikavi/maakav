"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Save, CheckCircle, Plus, Trash2 } from "lucide-react";
import api from "@/lib/api";
import NumberInput from "@/components/ui/NumberInput";
import { formatCurrency } from "@/lib/formatters";

type GuaranteeKind = "sale_law" | "land_owner" | "free_text";
interface GuaranteeFramework {
  label: string;
  amount: string;
  kind: GuaranteeKind;
}
interface PreProjectInvestment {
  label: string;
  amount: string;
  approved_by: string;
}

const DEFAULT_GUARANTEE_ROWS: GuaranteeFramework[] = [
  { label: "ערבות חוק מכר", amount: "", kind: "sale_law" },
  { label: "מסגרת ערבות לבעלי קרקע", amount: "", kind: "land_owner" },
];

interface ProjectIndexes {
  base_index: string | number | null;
  base_index_date: string | null;
  contractor_base_index: string | number | null;
  contractor_base_index_date: string | null;
}

const toMonthInput = (iso: string | null | undefined): string => {
  if (!iso) return "";
  const m = iso.match(/^(\d{4})-(\d{2})/);
  return m ? `${m[1]}-${m[2]}` : "";
};

const fromMonthInput = (yyyymm: string): string | null => {
  if (!yyyymm) return null;
  const m = yyyymm.match(/^(\d{4})-(\d{2})$/);
  return m ? `${m[1]}-${m[2]}-01` : null;
};

export default function FinancingSetupPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState({
    financing_type: "", financing_body: "",
    credit_limit_total: "", credit_limit_construction: "",
    credit_limit_land: "", credit_limit_guarantees: "", equity_required_amount: "",
    equity_required_percent: "", presale_units_required: "", presale_amount_required: "",
    equity_required_after_presale: "",
    interest_rate: "", guarantee_fee_percent: "", notes: "",
  });
  const [indexes, setIndexes] = useState({
    base_index: "", base_index_date: "",
    contractor_base_index: "", contractor_base_index_date: "",
  });
  const [guarantees, setGuarantees] = useState<GuaranteeFramework[]>(DEFAULT_GUARANTEE_ROWS);
  const [investments, setInvestments] = useState<PreProjectInvestment[]>([]);

  const { data: financing } = useQuery({
    queryKey: ["financing", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/setup/financing`)).data,
  });
  const { data: project } = useQuery<ProjectIndexes>({
    queryKey: ["project", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}`)).data,
  });
  const { data: equitySummary } = useQuery<{ budget_equity_total: number }>({
    queryKey: ["financing-equity-summary", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/setup/financing/equity-summary`)).data,
  });
  const budgetEquityTotal = Number(equitySummary?.budget_equity_total) || 0;

  type FinancingBodyGroup = {
    kind: string;
    label: string;
    bodies: { key: string; label: string; kind: string }[];
  };
  const { data: bodiesPayload } = useQuery<{ groups: FinancingBodyGroup[] }>({
    queryKey: ["financing-bodies"],
    queryFn: async () => (await api.get(`/setup/financing-bodies`)).data,
    staleTime: 1000 * 60 * 60,
  });

  useEffect(() => {
    if (financing) {
      setForm({
        financing_type: financing.financing_type || "",
        financing_body: financing.financing_body || "",
        credit_limit_total: financing.credit_limit_total?.toString() || "",
        credit_limit_construction: financing.credit_limit_construction?.toString() || "",
        credit_limit_land: financing.credit_limit_land?.toString() || "",
        credit_limit_guarantees: financing.credit_limit_guarantees?.toString() || "",
        equity_required_amount: financing.equity_required_amount?.toString() || "",
        equity_required_percent: financing.equity_required_percent?.toString() || "",
        presale_units_required: financing.presale_units_required?.toString() || "",
        presale_amount_required: financing.presale_amount_required?.toString() || "",
        equity_required_after_presale: financing.equity_required_after_presale?.toString() || "",
        interest_rate: financing.interest_rate?.toString() || "",
        guarantee_fee_percent: financing.guarantee_fee_percent?.toString() || "",
        notes: financing.notes || "",
      });
      const stored: GuaranteeFramework[] | null = financing.guarantee_frameworks;
      if (stored && stored.length > 0) {
        setGuarantees(stored.map((g) => ({
          label: g.label || "",
          amount: g.amount?.toString() || "",
          kind: (g.kind as GuaranteeKind) || "free_text",
        })));
      }
      const inv: PreProjectInvestment[] | null = financing.pre_project_investments;
      if (inv && inv.length > 0) {
        setInvestments(inv.map((it) => ({
          label: it.label || "",
          amount: it.amount?.toString() || "",
          approved_by: it.approved_by || "",
        })));
      }
    }
  }, [financing]);

  useEffect(() => {
    if (project) {
      setIndexes({
        base_index: project.base_index?.toString() || "",
        base_index_date: toMonthInput(project.base_index_date),
        contractor_base_index: project.contractor_base_index?.toString() || "",
        contractor_base_index_date: toMonthInput(project.contractor_base_index_date),
      });
    }
  }, [project]);

  const guaranteeTotal = guarantees.reduce((s, g) => s + (Number(g.amount) || 0), 0);
  const manualInvestmentsTotal = investments.reduce((s, it) => s + (Number(it.amount) || 0), 0);
  // Total recognized equity = manual rows on this screen + auto-computed
  // sum from per-line budget equity_investment values.
  const investmentsTotal = manualInvestmentsTotal + budgetEquityTotal;
  const equityRequired = Number(form.equity_required_amount) || 0;
  const equityRemaining = Math.max(0, equityRequired - investmentsTotal);

  const mutation = useMutation({
    mutationFn: async () => {
      const finPayload: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(form)) {
        if (value !== "" && key !== "credit_limit_guarantees") finPayload[key] = value;
      }
      finPayload.guarantee_frameworks = guarantees
        .filter((g) => g.label.trim() || g.amount)
        .map((g) => ({ label: g.label.trim(), amount: g.amount || null, kind: g.kind }));
      finPayload.pre_project_investments = investments
        .filter((it) => it.label.trim() || it.amount)
        .map((it) => ({ label: it.label.trim(), amount: it.amount || null, approved_by: it.approved_by.trim() || null }));
      const projPayload: Record<string, unknown> = {
        base_index: indexes.base_index || null,
        base_index_date: fromMonthInput(indexes.base_index_date),
        contractor_base_index: indexes.contractor_base_index || null,
        contractor_base_index_date: fromMonthInput(indexes.contractor_base_index_date),
      };
      await Promise.all([
        api.put(`/projects/${projectId}/setup/financing`, finPayload),
        api.patch(`/projects/${projectId}`, projPayload),
      ]);
    },
    onSuccess: () => {
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      queryClient.invalidateQueries({ queryKey: ["setup-status", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["financing", projectId] });
    },
  });

  const set = (field: string, value: string) => setForm((p) => ({ ...p, [field]: value }));
  const setIdx = (field: string, value: string) => setIndexes((p) => ({ ...p, [field]: value }));

  // Auto-percent: equity / (equity + bank credit) * 100
  const setEquityAmount = (val: string) => {
    setForm((p) => {
      const next = { ...p, equity_required_amount: val };
      const amount = Number(val);
      const credit = Number(p.credit_limit_total);
      if (amount > 0 && credit > 0) {
        const pct = (amount / (amount + credit)) * 100;
        next.equity_required_percent = pct.toFixed(2);
      } else if (val === "") {
        next.equity_required_percent = "";
      }
      return next;
    });
  };
  const setEquityPercent = (val: string) => {
    setForm((p) => {
      const next = { ...p, equity_required_percent: val };
      const pct = Number(val);
      const credit = Number(p.credit_limit_total);
      if (pct > 0 && pct < 100 && credit > 0) {
        const amount = (credit * pct) / (100 - pct);
        next.equity_required_amount = Math.round(amount).toString();
      } else if (val === "") {
        next.equity_required_amount = "";
      }
      return next;
    });
  };

  return (
    <div className="max-w-2xl mx-auto">
      <button onClick={() => router.push(`/projects/${projectId}`)} className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4 transition">
        <ArrowRight size={18} /> חזרה לפרויקט
      </button>

      <h1 className="text-2xl font-bold text-gray-900 mb-2">תנאי מימון</h1>
      <p className="text-gray-500 mb-6">הסכם ליווי, מסגרות אשראי, מדדים והון עצמי נדרש</p>

      <div className="bg-white rounded-2xl border border-gray-200 p-8 space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">סוג מימון</label>
            <select value={form.financing_type} onChange={(e) => set("financing_type", e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary">
              <option value="">בחר...</option>
              <option value="banking">בנקאי</option>
              <option value="non_banking">חוץ בנקאי</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">גוף מימון</label>
            <select value={form.financing_body} onChange={(e) => set("financing_body", e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary">
              <option value="">בחר...</option>
              {(bodiesPayload?.groups || []).map((g) => (
                <optgroup key={g.kind} label={g.label}>
                  {g.bodies.map((b) => (
                    <option key={b.key} value={b.key}>{b.label}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
        </div>

        <h3 className="font-bold text-gray-900 pt-2">מסגרות אשראי</h3>
        <div className="grid grid-cols-2 gap-4">
          <NumField label="מסגרת אשראי כוללת" value={form.credit_limit_total} onChange={(v) => set("credit_limit_total", v)} />
          <NumField label="מסגרת הקמה" value={form.credit_limit_construction} onChange={(v) => set("credit_limit_construction", v)} />
          <NumField label="מסגרת קרקע" value={form.credit_limit_land} onChange={(v) => set("credit_limit_land", v)} />
        </div>

        <h3 className="font-bold text-gray-900 pt-2">ערבויות הפרוייקט</h3>
        <p className="text-xs text-gray-500 -mt-3">פירוט מסגרות הערבויות. ניתן להוסיף שורות חופשיות לפי הצורך.</p>
        <div className="space-y-2">
          {guarantees.map((g, i) => (
            <div key={i} className="grid grid-cols-[1fr_180px_36px] gap-2 items-center">
              <input
                type="text"
                value={g.label}
                onChange={(e) => setGuarantees((prev) => prev.map((p, idx) => idx === i ? { ...p, label: e.target.value } : p))}
                placeholder="שם המסגרת"
                disabled={g.kind !== "free_text"}
                className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary disabled:bg-gray-50 disabled:text-gray-700 disabled:font-medium"
              />
              <NumberInput
                value={g.amount}
                onChange={(v) => setGuarantees((prev) => prev.map((p, idx) => idx === i ? { ...p, amount: v } : p))}
                placeholder="₪"
                className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
              <button
                type="button"
                onClick={() => setGuarantees((prev) => prev.filter((_, idx) => idx !== i))}
                disabled={guarantees.length <= 1}
                className="text-gray-400 hover:text-red-500 disabled:text-gray-200 disabled:cursor-not-allowed transition flex items-center justify-center"
                title="הסר"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => setGuarantees((prev) => [...prev, { label: "", amount: "", kind: "free_text" }])}
            className="flex items-center gap-1.5 text-sm text-primary hover:text-primary-dark transition"
          >
            <Plus size={14} /> הוסף שורה
          </button>
          <div className="flex justify-between items-center pt-3 mt-2 border-t border-gray-100">
            <span className="text-sm font-medium text-gray-700">סה״כ ערבויות</span>
            <span className="text-base font-bold text-gray-900">{formatCurrency(guaranteeTotal)}</span>
          </div>
        </div>

        <h3 className="font-bold text-gray-900 pt-2">הון עצמי ומכירות מוקדמות</h3>
        <div className="grid grid-cols-2 gap-4">
          <NumField label="הון עצמי נדרש (₪)" value={form.equity_required_amount} onChange={setEquityAmount} />
          <NumField label="הון עצמי נדרש (%)" value={form.equity_required_percent} onChange={setEquityPercent} />
          <NumField label="יחידות מכר מוקדם" value={form.presale_units_required} onChange={(v) => set("presale_units_required", v)} />
          <NumField label="סכום מכר מוקדם (₪)" value={form.presale_amount_required} onChange={(v) => set("presale_amount_required", v)} />
          <div className="col-span-2">
            <NumField
              label="הון עצמי לאחר עמידה בתנאי מכר מוקדם (₪) — אופציונלי"
              value={form.equity_required_after_presale}
              onChange={(v) => set("equity_required_after_presale", v)}
            />
            <p className="text-xs text-gray-500 mt-1">
              במידה ולאחר עמידה בתנאי המכר המוקדם ההון העצמי הנדרש משתנה — יש לציין כאן.
            </p>
          </div>
        </div>

        {(form.presale_amount_required || form.presale_units_required) && (
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-3 text-sm text-blue-900">
            <span className="font-bold">תנאי לקבלת מימון: </span>
            מכירות מוקדמות בסכום כולל של לפחות{" "}
            <span className="font-bold">{formatCurrency(Number(form.presale_amount_required) || 0)}</span>
            {" "}ו-{" "}
            <span className="font-bold">{form.presale_units_required || 0}</span>
            {" "}יחידות.
            {form.equity_required_after_presale && (
              <>
                {" "}לאחר עמידה בתנאי, ההון העצמי הנדרש{" "}
                <span className="font-bold">{formatCurrency(Number(form.equity_required_after_presale) || 0)}</span>.
              </>
            )}
          </div>
        )}

        <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-bold text-gray-900">השקעות טרום פרויקט</h4>
            <span className="text-xs text-gray-500">מוכרות כחלק מההון העצמי הנדרש</span>
          </div>
          <p className="text-xs text-gray-500 mb-3">סכומים שכבר הושקעו על ידי הקבלן ואושרו על ידי משרד שמאים.</p>

          {budgetEquityTotal > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 px-3 py-2 mb-3 flex items-center justify-between text-sm">
              <div>
                <span className="font-medium text-gray-700">מהשקעות בקובץ התקציב </span>
                <span className="text-xs text-gray-400">(נקרא אוטומטית מעמודת &quot;השקעות הון עצמי&quot;)</span>
              </div>
              <span className="font-bold text-gray-900">{formatCurrency(budgetEquityTotal)}</span>
            </div>
          )}
          <div className="space-y-2">
            {investments.length === 0 && (
              <p className="text-xs text-gray-400 text-center py-2">אין השקעות מתועדות</p>
            )}
            {investments.map((it, i) => (
              <div key={i} className="grid grid-cols-[1fr_180px_140px_36px] gap-2 items-center">
                <input
                  type="text"
                  value={it.label}
                  onChange={(e) => setInvestments((prev) => prev.map((p, idx) => idx === i ? { ...p, label: e.target.value } : p))}
                  placeholder="תיאור (לדוגמה: רכישת קרקע)"
                  className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
                <NumberInput
                  value={it.amount}
                  onChange={(v) => setInvestments((prev) => prev.map((p, idx) => idx === i ? { ...p, amount: v } : p))}
                  placeholder="₪"
                  className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
                <input
                  type="text"
                  value={it.approved_by}
                  onChange={(e) => setInvestments((prev) => prev.map((p, idx) => idx === i ? { ...p, approved_by: e.target.value } : p))}
                  placeholder="אושר על ידי..."
                  className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
                <button
                  type="button"
                  onClick={() => setInvestments((prev) => prev.filter((_, idx) => idx !== i))}
                  className="text-gray-400 hover:text-red-500 transition flex items-center justify-center"
                  title="הסר"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={() => setInvestments((prev) => [...prev, { label: "", amount: "", approved_by: "" }])}
              className="flex items-center gap-1.5 text-sm text-primary hover:text-primary-dark transition"
            >
              <Plus size={14} /> הוסף השקעה
            </button>
          </div>
          {(equityRequired > 0 || investmentsTotal > 0) && (
            <div className="grid grid-cols-3 gap-3 mt-4 pt-3 border-t border-gray-200 text-center">
              <div>
                <p className="text-xs text-gray-500">סה״כ השקעות</p>
                <p className="text-base font-bold text-gray-900">{formatCurrency(investmentsTotal)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">הון עצמי נדרש</p>
                <p className="text-base font-bold text-gray-700">{formatCurrency(equityRequired)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">יתרה להשלמה</p>
                <p className={`text-base font-bold ${equityRemaining === 0 ? "text-green-600" : "text-amber-600"}`}>
                  {formatCurrency(equityRemaining)}
                </p>
              </div>
            </div>
          )}
        </div>

        <h3 className="font-bold text-gray-900 pt-2">מדדי הפרוייקט</h3>
        <p className="text-xs text-gray-500 -mt-3">מדד הבסיס מתועד בדוח 0 — יש לציין את הערך וחודש/שנת הקריאה.</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">מדד תשומות הבנייה - בסיס</label>
            <NumberInput value={indexes.base_index} onChange={(v) => setIdx("base_index", v)} decimals={4}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">חודש/שנה (mm/yyyy)</label>
            <input type="month" value={indexes.base_index_date} onChange={(e) => setIdx("base_index_date", e.target.value)} dir="ltr"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">מדד הסכם הקבלן - בסיס</label>
            <NumberInput value={indexes.contractor_base_index} onChange={(v) => setIdx("contractor_base_index", v)} decimals={4}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">חודש/שנה (mm/yyyy)</label>
            <input type="month" value={indexes.contractor_base_index_date} onChange={(e) => setIdx("contractor_base_index_date", e.target.value)} dir="ltr"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary" />
          </div>
        </div>

        <details className="pt-2">
          <summary className="font-bold text-gray-700 cursor-pointer hover:text-gray-900">תנאים פיננסיים נוספים (אופציונלי)</summary>
          <div className="grid grid-cols-2 gap-4 mt-4">
            <NumField label="ריבית (%)" value={form.interest_rate} onChange={(v) => set("interest_rate", v)} />
            <NumField label="עמלת ערבות (%)" value={form.guarantee_fee_percent} onChange={(v) => set("guarantee_fee_percent", v)} />
          </div>
        </details>

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
