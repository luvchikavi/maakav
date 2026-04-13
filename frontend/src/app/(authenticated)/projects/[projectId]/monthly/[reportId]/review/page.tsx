"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft, ChevronRight, CheckCircle2, XCircle, AlertTriangle,
  ClipboardCheck, Calculator, Receipt, TrendingUp, Landmark, BarChart3,
} from "lucide-react";
import api from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/formatters";

interface DataCompleteness {
  bank_statement_uploaded: boolean;
  all_transactions_classified: boolean;
  construction_progress_entered: boolean;
  index_updated: boolean;
  ready_to_generate: boolean;
  missing_items: string[];
}

const CATEGORY_LABELS: Record<string, string> = {
  tenant_expenses: "קרקע והוצאות דיירים",
  land_and_taxes: "קרקע ומיסוי",
  indirect_costs: "כלליות",
  direct_construction: "בניה ישירה",
  extraordinary: "חריגות",
};

export default function ReviewStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [calcResults, setCalcResults] = useState<Record<string, unknown> | null>(null);
  const [calcErrors, setCalcErrors] = useState<string[]>([]);

  const { data: completeness } = useQuery<DataCompleteness>({
    queryKey: ["completeness", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/completeness`)).data,
  });

  const calculateMutation = useMutation({
    mutationFn: async () => {
      return api.post(`/projects/${projectId}/monthly-reports/${reportId}/calculate`);
    },
    onSuccess: (res) => {
      setCalcResults(res.data.results);
      setCalcErrors(res.data.errors || []);
      queryClient.invalidateQueries({ queryKey: ["completeness", reportId] });
    },
  });

  const checks = completeness ? [
    { label: "תדפיס בנק הועלה", done: completeness.bank_statement_uploaded },
    { label: "כל התנועות מסווגות", done: completeness.all_transactions_classified },
    { label: "התקדמות בנייה הוזנה", done: completeness.construction_progress_entered },
    { label: "מדד תשומות עודכן", done: completeness.index_updated },
  ] : [];

  const budget = calcResults?.budget_tracking as Record<string, unknown> | undefined;
  const sales = calcResults?.sales as Record<string, unknown> | undefined;
  const vat = calcResults?.vat as Record<string, unknown> | undefined;
  const equity = calcResults?.equity as Record<string, unknown> | undefined;
  const profitability = calcResults?.profitability as Record<string, unknown> | undefined;

  return (
    <div>
      {/* Completeness checklist */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <ClipboardCheck size={22} className="text-primary" />
          בדיקת שלמות נתונים
        </h2>
        <div className="grid grid-cols-2 gap-3 mb-4">
          {checks.map((check, i) => (
            <div key={i} className={`flex items-center gap-2 p-3 rounded-xl ${
              check.done ? "bg-green-50" : "bg-red-50"
            }`}>
              {check.done ? <CheckCircle2 size={18} className="text-green-600" /> : <XCircle size={18} className="text-red-500" />}
              <span className={`text-sm font-medium ${check.done ? "text-green-800" : "text-red-800"}`}>{check.label}</span>
            </div>
          ))}
        </div>

        {completeness?.missing_items && completeness.missing_items.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle size={16} className="text-amber-600" />
              <span className="text-sm font-bold text-amber-800">חסר:</span>
            </div>
            <ul className="list-disc list-inside text-sm text-amber-700">
              {completeness.missing_items.map((item, i) => <li key={i}>{item}</li>)}
            </ul>
          </div>
        )}
      </div>

      {/* Calculate button */}
      <button
        onClick={() => calculateMutation.mutate()}
        disabled={calculateMutation.isPending}
        className="w-full mb-6 py-4 rounded-2xl bg-primary text-white font-bold text-lg hover:bg-primary-dark transition disabled:opacity-50 flex items-center justify-center gap-3"
      >
        {calculateMutation.isPending ? (
          <><div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" /> מחשב...</>
        ) : (
          <><Calculator size={22} /> הרץ חישובים</>
        )}
      </button>

      {/* Calculation errors */}
      {calcErrors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-4 mb-6">
          {calcErrors.map((err, i) => <p key={i} className="text-red-700 text-sm">{err}</p>)}
        </div>
      )}

      {/* Results */}
      {calcResults && (
        <div className="space-y-4">
          {/* Budget tracking summary */}
          {budget && (
            <ResultCard icon={<Receipt size={20} />} title="נספח א' - ריכוז הוצאות" color="blue">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-gray-500 border-b">
                      <th className="text-right py-2 px-3">סעיף</th>
                      <th className="text-left py-2 px-3">תקציב (T1)</th>
                      <th className="text-left py-2 px-3">שולם חודשי (K)</th>
                      <th className="text-left py-2 px-3">מצטבר (L)</th>
                      <th className="text-left py-2 px-3">יתרה</th>
                      <th className="text-left py-2 px-3">ביצוע %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {(budget.lines as Array<Record<string, string>>)?.map((line, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="py-2 px-3 font-medium">{CATEGORY_LABELS[line.category] || line.category}</td>
                        <td className="py-2 px-3 text-left">{formatCurrency(parseFloat(line.original_budget))}</td>
                        <td className="py-2 px-3 text-left">{formatCurrency(parseFloat(line.monthly_paid_actual))}</td>
                        <td className="py-2 px-3 text-left">{formatCurrency(parseFloat(line.cumulative_actual))}</td>
                        <td className="py-2 px-3 text-left">{formatCurrency(parseFloat(line.remaining_indexed))}</td>
                        <td className="py-2 px-3 text-left font-bold">{formatPercent(parseFloat(line.execution_percent))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ResultCard>
          )}

          {/* Sales summary */}
          {sales && (
            <ResultCard icon={<BarChart3 size={20} />} title="מכירות" color="green">
              <div className="grid grid-cols-4 gap-3">
                <Stat label="נמכרו" value={`${sales.total_sold}`} sub={formatPercent(sales.sold_percent as number)} />
                <Stat label="מוכרות (>15%)" value={`${sales.recognized_by_bank}`} sub={formatPercent(sales.recognized_percent as number)} />
                <Stat label="למכירה" value={`${sales.unsold}`} />
                <Stat label="לא ליניאריות" value={`${sales.non_linear_count}`} />
              </div>
            </ResultCard>
          )}

          {/* VAT */}
          {vat && (
            <ResultCard icon={<Receipt size={20} />} title='מע"מ' color="purple">
              <div className="grid grid-cols-3 gap-3">
                <Stat label='מע"מ עסקאות' value={formatCurrency(parseFloat(vat.output_vat as string))} />
                <Stat label='מע"מ תשומות' value={formatCurrency(parseFloat(vat.input_vat as string))} />
                <Stat label="יתרה" value={formatCurrency(parseFloat(vat.vat_balance as string))} highlight />
              </div>
            </ResultCard>
          )}

          {/* Equity */}
          {equity && (
            <ResultCard icon={<Landmark size={20} />} title="הון עצמי" color="amber">
              <div className="grid grid-cols-3 gap-3">
                <Stat label="נדרש" value={formatCurrency(parseFloat(equity.required_amount as string))} />
                <Stat label="נוכחי" value={formatCurrency(parseFloat(equity.current_balance as string))} />
                <Stat label="עודף / (חסר)" value={formatCurrency(parseFloat(equity.gap as string))} highlight />
              </div>
            </ResultCard>
          )}

          {/* Profitability */}
          {profitability && (
            <ResultCard icon={<TrendingUp size={20} />} title="רווחיות" color="teal">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-xl p-4">
                  <p className="text-xs text-gray-500 mb-1">דוח אפס</p>
                  <p className="text-lg font-bold">{formatPercent(parseFloat(profitability.profit_percent_report_0 as string))}</p>
                  <p className="text-xs text-gray-400">רווח: {formatCurrency(parseFloat(profitability.profit_report_0 as string))}</p>
                </div>
                <div className="bg-primary/5 rounded-xl p-4">
                  <p className="text-xs text-gray-500 mb-1">נוכחי</p>
                  <p className="text-lg font-bold text-primary">{formatPercent(parseFloat(profitability.profit_percent_current as string))}</p>
                  <p className="text-xs text-gray-400">רווח: {formatCurrency(parseFloat(profitability.profit_current as string))}</p>
                </div>
              </div>
            </ResultCard>
          )}
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between mt-6">
        <button onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/guarantees`)}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition">
          <ChevronRight size={18} /> חזרה
        </button>
        <button
          onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/generate`)}
          disabled={!calcResults}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          המשך להפקת דוח <ChevronLeft size={18} />
        </button>
      </div>
    </div>
  );
}

function ResultCard({
  icon, title, color, children,
}: {
  icon: React.ReactNode; title: string; color: string; children: React.ReactNode;
}) {
  const colors: Record<string, string> = {
    blue: "border-blue-200 bg-blue-50/30",
    green: "border-green-200 bg-green-50/30",
    purple: "border-purple-200 bg-purple-50/30",
    amber: "border-amber-200 bg-amber-50/30",
    teal: "border-teal-200 bg-teal-50/30",
  };

  return (
    <div className={`rounded-2xl border p-5 ${colors[color] || "border-gray-200"}`}>
      <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2">{icon} {title}</h3>
      {children}
    </div>
  );
}

function Stat({ label, value, sub, highlight }: { label: string; value: string; sub?: string; highlight?: boolean }) {
  return (
    <div className={`rounded-xl p-3 text-center ${highlight ? "bg-primary/10" : "bg-white"}`}>
      <p className={`text-lg font-bold ${highlight ? "text-primary" : "text-gray-900"}`}>{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
      {sub && <p className="text-xs text-primary font-medium">{sub}</p>}
    </div>
  );
}
