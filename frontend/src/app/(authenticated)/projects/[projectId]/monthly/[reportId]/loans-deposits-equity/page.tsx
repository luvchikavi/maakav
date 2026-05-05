"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft, ChevronRight, Coins, Save, Plus, Trash2, RotateCcw,
} from "lucide-react";
import api from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/formatters";
import NumberInput from "@/components/ui/NumberInput";

type LoanItem = {
  label: string;
  kind: "senior" | "mezzanine" | "other";
  principal: number | null;
  current_balance: number | null;
  prev_month: number | null;
};

type DepositItem = {
  label: string;
  principal: number | null;
  current_balance: number | null;
  prev_month: number | null;
  accrued_interest: number | null;
};

type EquityComponent = {
  label: string;
  amount: number;
  source: string;
};

type Payload = {
  as_of: string | null;
  loans: LoanItem[];
  deposits: DepositItem[];
  equity: {
    components: EquityComponent[];
    current_balance: number;
    required_amount: number;
    gap: number;
  };
  notes: string | null;
};

const blankLoan = (): LoanItem => ({
  label: "", kind: "other", principal: null, current_balance: null, prev_month: null,
});
const blankDeposit = (): DepositItem => ({
  label: 'פיקדון פק"מ', principal: null, current_balance: null, prev_month: null, accrued_interest: null,
});

const diff = (curr: number | null, prev: number | null): number | null => {
  if (curr == null || prev == null) return null;
  return Number(curr) - Number(prev);
};

const eq = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

export default function LoansDepositsEquityStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<Payload>({
    queryKey: ["loans-deposits-equity", reportId],
    queryFn: async () => (await api.get(
      `/projects/${projectId}/monthly-reports/${reportId}/loans-deposits-equity`
    )).data,
  });

  const [loans, setLoans] = useState<LoanItem[]>([]);
  const [deposits, setDeposits] = useState<DepositItem[]>([]);
  const [asOf, setAsOf] = useState<string>("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (!data) return;
    setLoans(data.loans.map((l) => ({ ...l })));
    setDeposits(data.deposits.map((d) => ({ ...d })));
    setAsOf(data.as_of || new Date().toISOString().slice(0, 10));
    setNotes(data.notes || "");
  }, [data]);

  const dirty = data ? (
    !eq(loans, data.loans) || !eq(deposits, data.deposits)
    || asOf !== (data.as_of || "") || notes !== (data.notes || "")
  ) : false;

  const saveMutation = useMutation({
    mutationFn: async () => {
      await api.put(
        `/projects/${projectId}/monthly-reports/${reportId}/loans-deposits-equity`,
        { loans, deposits, as_of: asOf || null, notes: notes || null },
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["loans-deposits-equity", reportId] });
    },
  });

  const updateLoan = (i: number, patch: Partial<LoanItem>) => {
    setLoans((p) => p.map((row, idx) => (idx === i ? { ...row, ...patch } : row)));
  };
  const updateDeposit = (i: number, patch: Partial<DepositItem>) => {
    setDeposits((p) => p.map((row, idx) => (idx === i ? { ...row, ...patch } : row)));
  };

  if (isLoading || !data) {
    return (
      <div className="flex justify-center py-12">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Equity recomputed locally from current draft so the user sees totals
  // update as they edit the loans/mezzanine rows.
  const draftMezzanine = loans
    .filter((l) => l.kind === "mezzanine")
    .reduce((s, l) => s + (Number(l.current_balance) || 0), 0);
  const components = data.equity.components.map((c) =>
    c.source === "loans" ? { ...c, amount: draftMezzanine } : c
  );
  const currentBalance = components.reduce((s, c) => s + (Number(c.amount) || 0), 0);
  const requiredAmount = data.equity.required_amount;
  const gap = currentBalance - requiredAmount;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Coins size={24} className="text-primary" />
            <h2 className="text-lg font-bold text-gray-900">הלוואות ופקדונות</h2>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-500">נכון לתאריך</label>
            <input
              type="date"
              value={asOf}
              onChange={(e) => setAsOf(e.target.value)}
              dir="ltr"
              className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          הנתונים מציגים יתרות הלוואות ופקדונות נכון לתאריך הדיווח. הפרשים מחושבים מול החודש הקודם.
        </p>

        {/* LOANS */}
        <div className="space-y-3 mb-6">
          {loans.map((loan, i) => {
            const d = diff(loan.current_balance, loan.prev_month);
            return (
              <div key={i} className="border border-gray-200 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={loan.label}
                      onChange={(e) => updateLoan(i, { label: e.target.value })}
                      placeholder="שם ההלוואה"
                      className="font-bold text-gray-900 bg-transparent border-b border-transparent hover:border-gray-200 focus:border-primary focus:outline-none px-1"
                    />
                    <select
                      value={loan.kind}
                      onChange={(e) => updateLoan(i, { kind: e.target.value as LoanItem["kind"] })}
                      className="text-xs px-2 py-0.5 rounded-md border border-gray-200 focus:outline-none focus:ring-1 focus:ring-primary/20"
                    >
                      <option value="senior">חוב בכיר</option>
                      <option value="mezzanine">מזניין/נחות</option>
                      <option value="other">אחר</option>
                    </select>
                  </div>
                  <button
                    onClick={() => setLoans((p) => p.filter((_, idx) => idx !== i))}
                    className="text-gray-300 hover:text-red-500 transition"
                    title="הסר"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <div className="grid grid-cols-5 gap-3">
                  <ValueCell label="קרן" value={loan.principal} onChange={(v) => updateLoan(i, { principal: v })} />
                  <ValueCell label='י.ס. (יתרת סגירה)' value={loan.current_balance} onChange={(v) => updateLoan(i, { current_balance: v })} bold />
                  <ComputedCell label="מימון צבור" value={
                    loan.current_balance != null && loan.principal != null
                      ? Number(loan.current_balance) - Number(loan.principal)
                      : null
                  } />
                  <ValueCell label="חודש קודם" value={loan.prev_month} onChange={(v) => updateLoan(i, { prev_month: v })} muted />
                  <DiffCell label="הפרש" diffValue={d} />
                </div>
              </div>
            );
          })}
          <button
            onClick={() => setLoans((p) => [...p, blankLoan()])}
            className="flex items-center gap-1.5 text-sm text-primary hover:text-primary-dark transition"
          >
            <Plus size={14} /> הוסף הלוואה
          </button>
        </div>

        {/* DEPOSITS */}
        <h3 className="font-bold text-gray-900 pt-2 mb-3">פקדונות</h3>
        <div className="space-y-3">
          {deposits.map((dep, i) => {
            const d = diff(dep.current_balance, dep.prev_month);
            return (
              <div key={i} className="border border-gray-200 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <input
                    type="text"
                    value={dep.label}
                    onChange={(e) => updateDeposit(i, { label: e.target.value })}
                    placeholder="שם הפיקדון"
                    className="font-bold text-gray-900 bg-transparent border-b border-transparent hover:border-gray-200 focus:border-primary focus:outline-none px-1"
                  />
                  <button
                    onClick={() => setDeposits((p) => p.filter((_, idx) => idx !== i))}
                    className="text-gray-300 hover:text-red-500 transition"
                    title="הסר"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <div className="grid grid-cols-5 gap-3">
                  <ValueCell label='סה"כ קרן' value={dep.principal} onChange={(v) => updateDeposit(i, { principal: v })} />
                  <ValueCell label='י.ס. פר"י' value={dep.current_balance} onChange={(v) => updateDeposit(i, { current_balance: v })} bold />
                  <ComputedCell label="ריבית לקבל" value={
                    dep.current_balance != null && dep.principal != null
                      ? Number(dep.current_balance) - Number(dep.principal)
                      : null
                  } />
                  <ValueCell label="חודש קודם" value={dep.prev_month} onChange={(v) => updateDeposit(i, { prev_month: v })} muted />
                  <DiffCell label="הפרש" diffValue={d} />
                </div>
              </div>
            );
          })}
          <button
            onClick={() => setDeposits((p) => [...p, blankDeposit()])}
            className="flex items-center gap-1.5 text-sm text-primary hover:text-primary-dark transition"
          >
            <Plus size={14} /> הוסף פיקדון
          </button>
        </div>
      </div>

      {/* EQUITY */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Coins size={24} className="text-primary" />
          <h2 className="text-lg font-bold text-gray-900">הון עצמי</h2>
        </div>

        <p className="text-sm text-gray-500 mb-3 font-bold">רכיבי ההון העצמי (סעיף 9.2)</p>
        <table className="w-full mb-4">
          <tbody>
            {components.map((c) => (
              <tr key={c.label} className="border-b border-gray-50">
                <td className="py-2.5 text-right text-sm text-gray-700">
                  {c.label}
                  {c.source === "manual" && (
                    <span className="text-xs text-amber-600 mr-2">— יש למלא ידנית</span>
                  )}
                  {c.source === "bank" && (
                    <span className="text-xs text-gray-400 mr-2">— מסיווגי תדפיס הבנק</span>
                  )}
                  {c.source === "budget+manual" && (
                    <span className="text-xs text-gray-400 mr-2">— מתקציב + השקעות טרום פרויקט</span>
                  )}
                  {c.source === "loans" && (
                    <span className="text-xs text-gray-400 mr-2">— מטבלת ההלוואות לעיל</span>
                  )}
                </td>
                <td className="py-2.5 text-left text-sm font-medium text-gray-900 whitespace-nowrap">
                  {formatCurrency(c.amount)}
                </td>
              </tr>
            ))}
            <tr>
              <td className="py-3 text-right text-sm font-bold text-gray-900">סה״כ הון עצמי נוכחי</td>
              <td className="py-3 text-left text-base font-bold text-gray-900 whitespace-nowrap">
                {formatCurrency(currentBalance)}
              </td>
            </tr>
          </tbody>
        </table>

        <p className="text-sm text-gray-500 mb-3 font-bold">בדיקת עמידה בדרישת הליווי</p>
        <table className="w-full">
          <tbody>
            <tr className="border-b border-gray-50">
              <td className="py-2.5 text-right text-sm text-gray-700">הון עצמי נדרש</td>
              <td className="py-2.5 text-left text-sm font-medium text-gray-900 whitespace-nowrap">
                {formatCurrency(requiredAmount)}
              </td>
            </tr>
            <tr className={`${gap < 0 ? "bg-red-50" : "bg-green-50"} rounded-lg`}>
              <td className="py-3 px-2 text-right text-sm font-bold">
                {gap >= 0 ? "הון עצמי עודף" : "הון עצמי בחוסר"}
              </td>
              <td className={`py-3 px-2 text-left text-base font-bold whitespace-nowrap ${gap < 0 ? "text-red-700" : "text-green-700"}`}>
                {gap < 0 ? `(${formatCurrency(Math.abs(gap))})` : formatCurrency(gap)}
              </td>
            </tr>
          </tbody>
        </table>

        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">הערות</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      {/* Save */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/construction`)}
            className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition"
          >
            <ChevronRight size={18} /> חזרה
          </button>
        </div>
        <div className="flex items-center gap-2">
          {dirty && (
            <button
              onClick={() => { setLoans(data.loans.map((l) => ({ ...l }))); setDeposits(data.deposits.map((d) => ({ ...d }))); setAsOf(data.as_of || ""); setNotes(data.notes || ""); }}
              className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
            >
              <RotateCcw size={14} /> בטל
            </button>
          )}
          <button
            onClick={() => saveMutation.mutate()}
            disabled={!dirty || saveMutation.isPending}
            className="flex items-center gap-2 px-5 py-2.5 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition disabled:opacity-50"
          >
            <Save size={16} />
            {saveMutation.isPending ? "שומר..." : dirty ? "שמור" : "נשמר"}
          </button>
          <button
            onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/guarantees`)}
            className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition"
          >
            המשך לערבויות <ChevronLeft size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

function ValueCell({ label, value, onChange, bold, muted }: {
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
  bold?: boolean;
  muted?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <NumberInput
        value={value === null ? "" : value}
        onChange={(v) => onChange(v === "" ? null : Number(v))}
        className={`w-full px-2 py-1.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 ${bold ? "font-bold" : ""} ${muted ? "text-gray-500" : ""}`}
      />
    </div>
  );
}

function ComputedCell({ label, value }: { label: string; value: number | null }) {
  return (
    <div>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-sm font-medium text-gray-700 py-1.5 bg-gray-50 rounded-lg px-2" dir="ltr">
        {value == null ? "—" : formatCurrency(value).replace(" ₪", "")}
      </p>
    </div>
  );
}

function DiffCell({ label, diffValue }: { label: string; diffValue: number | null }) {
  const negative = (diffValue ?? 0) < 0;
  return (
    <div>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-sm font-bold py-1.5 ${diffValue == null ? "text-gray-400" : negative ? "text-red-600" : "text-green-600"}`} dir="ltr">
        {diffValue == null
          ? "—"
          : negative
            ? `(${formatCurrency(Math.abs(diffValue)).replace(" ₪", "")})`
            : formatCurrency(diffValue).replace(" ₪", "")}
      </p>
    </div>
  );
}
