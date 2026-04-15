"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft, ChevronRight, CheckCircle2, XCircle, AlertTriangle,
  ClipboardCheck, Calculator, Receipt, TrendingUp, Landmark, BarChart3,
  Shield, Activity,
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
  const vatHistory = calcResults?.vat_history as Array<Record<string, string>> | undefined;
  const equity = calcResults?.equity as Record<string, unknown> | undefined;
  const profitability = calcResults?.profitability as Record<string, unknown> | undefined;
  const expenseForecast = calcResults?.expense_forecast as Record<string, string> | undefined;

  // Fetch exposure + cashflow after calculations run
  const { data: exposure } = useQuery({
    queryKey: ["exposure", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/exposure`)).data,
    enabled: !!calcResults,
  });

  const { data: cashflow } = useQuery({
    queryKey: ["cashflow", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/cashflow`)).data,
    enabled: !!calcResults,
  });

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
            <ResultCard icon={<Receipt size={20} />} title={"נספח א' - פירוט הוצאות (תקציב וניצולו)"} color="blue">
              <div className="text-xs text-gray-500 mb-2 flex gap-4">
                <span>מדד בסיס: {budget.base_index as string}</span>
                <span>מדד נוכחי: {budget.current_index as string}</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-[10px] text-gray-500 border-b bg-gray-50">
                      <th className="text-right py-2 px-2 font-medium sticky right-0 bg-gray-50">סעיף</th>
                      <th className="text-left py-2 px-2 font-medium">תקציב מקורי<br/>(T1)</th>
                      <th className="text-left py-2 px-2 font-medium">העברות<br/>(T2)</th>
                      <th className="text-left py-2 px-2 font-medium">תקציב צמוד<br/>(A=T1+T2)</th>
                      <th className="text-left py-2 px-2 font-medium">שולם מצטבר<br/>קודם (D1)</th>
                      <th className="text-left py-2 px-2 font-medium">שולם חודשי<br/>(D2)</th>
                      <th className="text-left py-2 px-2 font-medium">שולם מצטבר<br/>נוכחי (S)</th>
                      <th className="text-left py-2 px-2 font-medium">יתרה לשלם<br/>(T1+T2-S)</th>
                      <th className="text-left py-2 px-2 font-medium">תקציב מתואם<br/>מדד (C)</th>
                      <th className="text-left py-2 px-2 font-medium">יתרה מתואמת<br/>(B)</th>
                      <th className="text-left py-2 px-2 font-medium">ביצוע %<br/>(A/C)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {(budget.lines as Array<Record<string, string>>)?.map((line, i) => {
                      const pct = parseFloat(line.execution_percent);
                      const pctColor = pct >= 100 ? "text-red-600 font-bold" : pct >= 90 ? "text-amber-600 font-bold" : pct >= 70 ? "text-blue-600" : "";
                      return (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="py-2 px-2 font-medium text-gray-900 sticky right-0 bg-white whitespace-nowrap">{CATEGORY_LABELS[line.category] || line.category}</td>
                          <td className="py-2 px-2 text-left">{formatCurrency(parseFloat(line.original_budget))}</td>
                          <td className="py-2 px-2 text-left">{formatCurrency(parseFloat(line.budget_transfer))}</td>
                          <td className="py-2 px-2 text-left font-medium">{formatCurrency(parseFloat(line.adjusted_indexed))}</td>
                          <td className="py-2 px-2 text-left text-gray-500">—</td>
                          <td className="py-2 px-2 text-left">{formatCurrency(parseFloat(line.monthly_paid_actual))}</td>
                          <td className="py-2 px-2 text-left font-medium">{formatCurrency(parseFloat(line.cumulative_actual))}</td>
                          <td className="py-2 px-2 text-left">{formatCurrency(parseFloat(line.remaining_base))}</td>
                          <td className="py-2 px-2 text-left">{formatCurrency(parseFloat(line.total_indexed))}</td>
                          <td className="py-2 px-2 text-left">{formatCurrency(parseFloat(line.remaining_indexed))}</td>
                          <td className={`py-2 px-2 text-left ${pctColor}`}>{formatPercent(pct)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                  {/* Totals row */}
                  <tfoot>
                    <tr className="border-t-2 border-gray-300 font-bold bg-gray-50">
                      <td className="py-2 px-2 text-gray-900 sticky right-0 bg-gray-50">סה&quot;כ</td>
                      <td className="py-2 px-2 text-left">{formatCurrency(parseFloat(budget.total_original_budget as string || "0"))}</td>
                      <td className="py-2 px-2 text-left">—</td>
                      <td className="py-2 px-2 text-left">—</td>
                      <td className="py-2 px-2 text-left">—</td>
                      <td className="py-2 px-2 text-left">{formatCurrency(parseFloat(budget.total_monthly_paid as string || "0"))}</td>
                      <td className="py-2 px-2 text-left">{formatCurrency(parseFloat(budget.total_cumulative_paid as string || "0"))}</td>
                      <td className="py-2 px-2 text-left">{formatCurrency(parseFloat(budget.total_remaining as string || "0"))}</td>
                      <td className="py-2 px-2 text-left" colSpan={3}></td>
                    </tr>
                  </tfoot>
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
            <ResultCard icon={<Receipt size={20} />} title='הפרשי מע"מ' color="purple">
              <div className="grid grid-cols-3 gap-3 mb-4">
                <Stat label='מע"מ עסקאות' value={formatCurrency(parseFloat(vat.output_vat as string))} />
                <Stat label='מע"מ תשומות' value={formatCurrency(parseFloat(vat.input_vat as string))} />
                <Stat label="יתרה חודשית (לקבל/לשלם)" value={formatCurrency(parseFloat(vat.vat_balance as string))} highlight />
              </div>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <Stat label="עסקאות (הכנסות)" value={formatCurrency(parseFloat(vat.transactions_total as string))} />
                <Stat label="תשומות (הוצאות)" value={formatCurrency(parseFloat(vat.inputs_total as string))} />
              </div>
              <Stat label="יתרה מצטברת" value={formatCurrency(parseFloat(vat.cumulative_vat_balance as string))} highlight />

              {/* Monthly VAT history table */}
              {vatHistory && vatHistory.length > 1 && (
                <div className="mt-4 pt-4 border-t">
                  <p className="text-xs font-bold text-gray-700 mb-2">מעקב מע&quot;מ חודשי</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-[10px]">
                      <thead>
                        <tr className="text-gray-500 border-b">
                          <th className="text-right py-1 px-1">חודש</th>
                          <th className="text-left py-1 px-1">עסקאות</th>
                          <th className="text-left py-1 px-1">מע&quot;מ עסקאות</th>
                          <th className="text-left py-1 px-1">תשומות</th>
                          <th className="text-left py-1 px-1">מע&quot;מ תשומות</th>
                          <th className="text-left py-1 px-1">יתרה חודשית</th>
                          <th className="text-left py-1 px-1 font-bold">מצטבר</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {vatHistory.map((v, i) => {
                          const bal = parseFloat(v.vat_balance);
                          return (
                            <tr key={i} className="hover:bg-gray-50">
                              <td className="py-1 px-1 font-medium">{v.month?.substring(0, 7)}</td>
                              <td className="py-1 px-1 text-left">{formatCurrency(parseFloat(v.transactions_total))}</td>
                              <td className="py-1 px-1 text-left">{formatCurrency(parseFloat(v.output_vat))}</td>
                              <td className="py-1 px-1 text-left">{formatCurrency(parseFloat(v.inputs_total))}</td>
                              <td className="py-1 px-1 text-left">{formatCurrency(parseFloat(v.input_vat))}</td>
                              <td className={`py-1 px-1 text-left ${bal >= 0 ? "text-green-600" : "text-red-600"}`}>{formatCurrency(bal)}</td>
                              <td className="py-1 px-1 text-left font-bold">{formatCurrency(parseFloat(v.cumulative_vat_balance))}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </ResultCard>
          )}

          {/* Equity */}
          {equity && (
            <ResultCard icon={<Landmark size={20} />} title="הון עצמי מצטבר" color="amber">
              <div className="grid grid-cols-3 gap-3 mb-4">
                <Stat label="הון עצמי נדרש" value={formatCurrency(parseFloat(equity.required_amount as string))} />
                <Stat label="הון עצמי נוכחי" value={formatCurrency(parseFloat(equity.current_balance as string))} />
                <Stat label="עודף / (חסר)" value={formatCurrency(parseFloat(equity.gap as string))} highlight />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Stat label="הפקדות מצטבר" value={formatCurrency(parseFloat(equity.total_deposits as string))} />
                <Stat label="משיכות מצטבר" value={formatCurrency(parseFloat(equity.total_withdrawals as string))} />
              </div>

              {/* Per-report equity history */}
              {(equity.history as Array<Record<string, string>> | undefined) && (
                <div className="mt-4 pt-4 border-t">
                  <p className="text-xs font-bold text-gray-700 mb-2">פירוט הפקדות/משיכות לפי דוח</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-[10px]">
                      <thead>
                        <tr className="text-gray-500 border-b">
                          <th className="text-right py-1 px-1">מס&apos; דוח</th>
                          <th className="text-left py-1 px-1">הפקדות</th>
                          <th className="text-left py-1 px-1">משיכות</th>
                          <th className="text-left py-1 px-1 font-bold">יתרה</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {(equity.history as Array<Record<string, string>>).map((h, i) => (
                          <tr key={i} className="hover:bg-gray-50">
                            <td className="py-1 px-1 font-medium">דוח {h.report_number}</td>
                            <td className="py-1 px-1 text-left text-green-600">{formatCurrency(parseFloat(h.deposits))}</td>
                            <td className="py-1 px-1 text-left text-red-600">{formatCurrency(parseFloat(h.withdrawals))}</td>
                            <td className="py-1 px-1 text-left font-bold">{formatCurrency(parseFloat(h.balance))}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
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

          {/* Expense Forecast */}
          {expenseForecast && (
            <ResultCard icon={<Calculator size={20} />} title="תחזית חודש הבא" color="purple">
              <div className="grid grid-cols-3 gap-3">
                <Stat label="יתרת תקציב" value={formatCurrency(parseFloat(expenseForecast.budget_remaining))} />
                <Stat label="הוצאות צפויות" value={formatCurrency(parseFloat(expenseForecast.estimated_monthly_expense))} />
                <Stat label="תקבולים צפויים" value={formatCurrency(parseFloat(expenseForecast.expected_receipts_next_month))} highlight />
              </div>
            </ResultCard>
          )}

          {/* Guarantee Validation */}
          {calcResults && (
            <GuaranteeValidationCard projectId={projectId} reportId={reportId} />
          )}

          {/* Exposure Report */}
          {exposure && (
            <ResultCard icon={<Shield size={20} />} title="דוח חשיפה" color="amber">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Stat label="% מכירות" value={formatPercent(exposure.sales_percent)} sub={`${exposure.sold_count}/${exposure.total_developer_units}`} />
                <Stat label="% בנייה" value={formatPercent(exposure.construction_percent)} />
                <Stat label="אשראי מנוצל" value={formatCurrency(exposure.credit_used)} sub={`${formatPercent(exposure.credit_utilization_percent)} מהמסגרת`} />
                <Stat label="חשיפה נטו" value={formatCurrency(exposure.net_exposure)} highlight />
              </div>
              <div className="grid grid-cols-3 gap-3 mt-3">
                <Stat label="מסגרת אשראי" value={formatCurrency(exposure.credit_limit)} />
                <Stat label="תקבולים מצטבר" value={formatCurrency(exposure.total_receipts)} />
                <Stat label="הון עצמי" value={formatCurrency(exposure.equity_balance)} />
              </div>
            </ResultCard>
          )}

          {/* Cashflow Forecast */}
          {cashflow && (
            <ResultCard icon={<Activity size={20} />} title="תזרים מזומנים (6 חודשים)" color="blue">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-gray-500 border-b">
                      <th className="text-right py-2 px-2">חודש</th>
                      <th className="text-left py-2 px-2">הכנסות צפויות</th>
                      <th className="text-left py-2 px-2">הוצאות צפויות</th>
                      <th className="text-left py-2 px-2">נטו</th>
                      <th className="text-left py-2 px-2">מצטבר</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {(cashflow.months as Array<Record<string, number | string>>)?.map((m, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="py-2 px-2 font-medium">{m.month as string}</td>
                        <td className="py-2 px-2 text-left text-green-600">{formatCurrency(m.projected_income as number)}</td>
                        <td className="py-2 px-2 text-left text-red-600">{formatCurrency(m.projected_expenses as number)}</td>
                        <td className={`py-2 px-2 text-left font-medium ${(m.net_flow as number) >= 0 ? "text-green-700" : "text-red-700"}`}>
                          {formatCurrency(m.net_flow as number)}
                        </td>
                        <td className={`py-2 px-2 text-left font-bold ${(m.cumulative_balance as number) >= 0 ? "text-green-800" : "text-red-800"}`}>
                          {formatCurrency(m.cumulative_balance as number)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t">
                <Stat label='סה"כ הכנסות' value={formatCurrency(cashflow.summary?.total_projected_income)} />
                <Stat label='סה"כ הוצאות' value={formatCurrency(cashflow.summary?.total_projected_expenses)} />
                <Stat label="נטו" value={formatCurrency(cashflow.summary?.total_net_flow)} highlight />
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

function GuaranteeValidationCard({ projectId, reportId }: { projectId: string; reportId: string }) {
  const { data } = useQuery({
    queryKey: ["guarantee-validation", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/guarantees/validate`)).data,
  });

  if (!data) return null;

  const { alerts, summary } = data;
  const hasAlerts = alerts && alerts.length > 0;

  return (
    <ResultCard
      icon={<Shield size={20} />}
      title="ערבויות — בדיקת תקינות"
      color={hasAlerts ? "amber" : "green"}
    >
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <Stat label="ערבויות חוק מכר" value={String(summary?.total_guarantees || 0)} />
        <Stat label='סה"כ ערבויות' value={formatCurrency(summary?.total_guarantee_amount || 0)} />
        <Stat label="תקבולים מצטבר" value={formatCurrency(summary?.total_receipts || 0)} />
        <Stat label="הפרש" value={formatCurrency(summary?.gap || 0)} highlight />
      </div>
      <div className="grid grid-cols-2 gap-3 mb-4">
        <Stat label="דירות שנמכרו" value={String(summary?.sold_apartments || 0)} />
        <Stat label="דירות עם ערבות" value={String(summary?.apartments_with_guarantee || 0)} />
      </div>

      {hasAlerts ? (
        <div className="space-y-2">
          <p className="text-xs font-bold text-amber-800">התראות:</p>
          {alerts.map((alert: { type: string; severity: string; message: string }, i: number) => (
            <div key={i} className={`flex items-start gap-2 p-2 rounded-lg text-xs ${
              alert.severity === "error" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"
            }`}>
              <AlertTriangle size={14} className="shrink-0 mt-0.5" />
              <span>{alert.message}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-2 p-3 bg-green-50 rounded-lg text-sm text-green-700">
          <CheckCircle2 size={16} />
          <span>כל הערבויות תקינות — אין התראות</span>
        </div>
      )}
    </ResultCard>
  );
}
