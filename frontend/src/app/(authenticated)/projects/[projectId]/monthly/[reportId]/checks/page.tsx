"use client";

import { useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft, ChevronRight, CreditCard, Upload, CheckCircle, AlertTriangle,
  Trash2, ThumbsUp, ThumbsDown, X, Link2, Sparkles, TrendingUp,
} from "lucide-react";
import api from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/formatters";

interface Check {
  id: number;
  serial_number: number;
  operation_type: string;
  check_number: string | null;
  amount_with_vat: number;
  amount_no_vat: number | null;
  beneficiary_name: string;
  due_date: string | null;
  description: string | null;
  budget_category: string | null;
  invoice_number: string | null;
  approval_status: string;
  payment_status: string;
  approved_by: string | null;
}

interface Summary {
  total_checks: number;
  pending_count: number;
  approved_count: number;
  paid_count: number;
  total_approved_amount: number;
  total_pending_amount: number;
  total_paid_amount: number;
  budget_alerts: Array<{ category: string; severity: string; message: string; usage_percent: number; remaining: number }>;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
};
const STATUS_LABELS: Record<string, string> = {
  pending: "ממתין",
  approved: "מאושר",
  rejected: "נדחה",
};
const PAYMENT_COLORS: Record<string, string> = {
  unpaid: "bg-gray-100 text-gray-700",
  paid: "bg-blue-100 text-blue-700",
};
const PAYMENT_LABELS: Record<string, string> = {
  unpaid: "לא שולם",
  paid: "שולם",
};

export default function ChecksStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ created: number; auto_matched: number } | null>(null);
  const [showForecast, setShowForecast] = useState(false);

  const { data: checks = [] } = useQuery<Check[]>({
    queryKey: ["checks", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/checks`)).data,
  });

  const { data: summary } = useQuery<Summary>({
    queryKey: ["checks-summary", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/checks/summary`)).data,
    enabled: checks.length > 0,
  });

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setUploadResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post(
        `/projects/${projectId}/monthly-reports/${reportId}/checks/upload`,
        formData,
      );
      setUploadResult(data);
      qc.invalidateQueries({ queryKey: ["checks", reportId] });
      qc.invalidateQueries({ queryKey: ["checks-summary", reportId] });
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "שגיאה בהעלאת הקובץ");
    } finally {
      setUploading(false);
    }
  }, [projectId, reportId, qc]);

  const approveMutation = useMutation({
    mutationFn: ({ checkId, status }: { checkId: number; status: string }) =>
      api.post(`/projects/${projectId}/monthly-reports/${reportId}/checks/${checkId}/approve`, { approval_status: status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["checks", reportId] });
      qc.invalidateQueries({ queryKey: ["checks-summary", reportId] });
    },
  });

  const autoGenMutation = useMutation({
    mutationFn: async () =>
      (await api.post(`/projects/${projectId}/monthly-reports/${reportId}/checks/auto-generate`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["checks", reportId] });
      qc.invalidateQueries({ queryKey: ["checks-summary", reportId] });
    },
  });

  const { data: forecast } = useQuery({
    queryKey: ["expense-forecast", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/expense-forecast`)).data,
    enabled: showForecast,
  });

  const deleteMutation = useMutation({
    mutationFn: (checkId: number) =>
      api.delete(`/projects/${projectId}/monthly-reports/${reportId}/checks/${checkId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["checks", reportId] });
      qc.invalidateQueries({ queryKey: ["checks-summary", reportId] });
    },
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Upload zone */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <CreditCard size={24} className="text-primary" />
          <h2 className="text-lg font-bold text-gray-900">אישורי שיקים והעברות</h2>
        </div>

        <div
          className="border-2 border-dashed border-gray-200 hover:border-primary/40 rounded-xl p-6 text-center cursor-pointer transition"
          onClick={() => {
            const input = document.createElement("input");
            input.type = "file";
            input.accept = ".xlsx,.xls";
            input.onchange = (e) => {
              const f = (e.target as HTMLInputElement).files?.[0];
              if (f) handleUpload(f);
            };
            input.click();
          }}
        >
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-gray-600 font-medium">מעבד קובץ...</p>
            </div>
          ) : (
            <div className="flex items-center justify-center gap-3">
              <Upload size={20} className="text-gray-400" />
              <div className="text-right">
                <p className="font-medium text-gray-700">העלה טאב חודשי של אישורי שיקים</p>
                <p className="text-sm text-gray-400">המערכת תזהה ותתאים אוטומטית לתנועות בנק</p>
              </div>
            </div>
          )}
        </div>

        {uploadResult && (
          <div className="mt-3 bg-green-50 rounded-xl border border-green-200 p-3 flex items-center gap-2">
            <CheckCircle size={18} className="text-green-600" />
            <span className="text-sm text-green-800">
              נוצרו {uploadResult.created} שיקים | {uploadResult.auto_matched} הותאמו אוטומטית לתנועות בנק
            </span>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 mt-4">
          <button
            onClick={() => autoGenMutation.mutate()}
            disabled={autoGenMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-xl text-sm font-medium hover:bg-purple-700 transition disabled:opacity-50"
          >
            <Sparkles size={16} />
            {autoGenMutation.isPending ? "יוצר..." : "ייצר טיוטות מתדפיס בנק"}
          </button>
          <button
            onClick={() => setShowForecast(!showForecast)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition ${
              showForecast ? "bg-primary text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            <TrendingUp size={16} />
            צפי הוצאות
          </button>
        </div>

        {autoGenMutation.isSuccess && (
          <div className="mt-2 bg-purple-50 rounded-xl border border-purple-200 p-3 flex items-center gap-2">
            <Sparkles size={16} className="text-purple-600" />
            <span className="text-sm text-purple-800">
              נוצרו {(autoGenMutation.data as any)?.generated || 0} טיוטות מתנועות בנק
              {(autoGenMutation.data as any)?.skipped ? ` (${(autoGenMutation.data as any).skipped} כבר קיימות)` : ""}
            </span>
          </div>
        )}
      </div>

      {/* Expense Forecast Panel */}
      {showForecast && forecast && (
        <div className="bg-white rounded-2xl border-2 border-primary/20 overflow-hidden">
          <div className="p-4 bg-primary/5 border-b border-primary/10">
            <h3 className="font-bold text-gray-900 flex items-center gap-2">
              <TrendingUp size={18} className="text-primary" />
              צפי הוצאות והכנסות
            </h3>
          </div>
          <div className="p-4 space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-red-50 rounded-xl p-3 text-center">
                <p className="text-lg font-bold text-red-700">{formatCurrency(forecast.summary?.total_unpaid || 0)}</p>
                <p className="text-xs text-red-600">שיקים מאושרים שטרם נפרעו ({forecast.summary?.unpaid_count})</p>
              </div>
              <div className="bg-amber-50 rounded-xl p-3 text-center">
                <p className="text-lg font-bold text-amber-700">{formatCurrency(forecast.summary?.total_pending || 0)}</p>
                <p className="text-xs text-amber-600">ממתינים לאישור ({forecast.summary?.pending_count})</p>
              </div>
              <div className="bg-green-50 rounded-xl p-3 text-center">
                <p className="text-lg font-bold text-green-700">{formatCurrency(forecast.summary?.total_future_receipts || 0)}</p>
                <p className="text-xs text-green-600">תקבולים צפויים ({forecast.summary?.future_receipts_count})</p>
              </div>
            </div>

            {/* Budget status with alerts */}
            {forecast.budget_status && forecast.budget_status.length > 0 && (
              <div>
                <p className="text-sm font-bold text-gray-700 mb-2">מצב תקציב לפי סעיף</p>
                <div className="space-y-2">
                  {forecast.budget_status.map((item: any, i: number) => (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-xs text-gray-600 w-28 shrink-0">{item.category}</span>
                      <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            item.usage_percent >= 100 ? "bg-red-500" : item.usage_percent >= 90 ? "bg-amber-500" : "bg-primary"
                          }`}
                          style={{ width: `${Math.min(item.usage_percent, 100)}%` }}
                        />
                      </div>
                      <span className={`text-xs font-bold w-12 text-left ${
                        item.usage_percent >= 100 ? "text-red-600" : item.usage_percent >= 90 ? "text-amber-600" : "text-gray-600"
                      }`}>
                        {item.usage_percent}%
                      </span>
                      <span className="text-[10px] text-gray-400 w-24 text-left">
                        יתרה: {formatCurrency(item.remaining)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Unpaid checks list */}
            {forecast.unpaid_checks && forecast.unpaid_checks.length > 0 && (
              <div>
                <p className="text-sm font-bold text-gray-700 mb-2">שיקים מאושרים — טרם נפרעו</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-gray-500 border-b">
                        <th className="text-right py-1 px-2">מוטב</th>
                        <th className="text-left py-1 px-2">סכום</th>
                        <th className="text-right py-1 px-2">תאריך פירעון</th>
                        <th className="text-right py-1 px-2">סעיף</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {forecast.unpaid_checks.map((c: any, i: number) => (
                        <tr key={i}>
                          <td className="py-1.5 px-2 font-medium">{c.beneficiary_name}</td>
                          <td className="py-1.5 px-2 text-left text-red-600 font-medium">{formatCurrency(c.amount_with_vat)}</td>
                          <td className="py-1.5 px-2 text-gray-600">{c.due_date ? formatDate(c.due_date) : "—"}</td>
                          <td className="py-1.5 px-2 text-gray-500">{c.budget_category || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Future receipts */}
            {forecast.future_receipts && forecast.future_receipts.length > 0 && (
              <div>
                <p className="text-sm font-bold text-gray-700 mb-2">תקבולים צפויים (מפריסת תשלומים)</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-gray-500 border-b">
                        <th className="text-right py-1 px-2">רוכש</th>
                        <th className="text-left py-1 px-2">סכום</th>
                        <th className="text-right py-1 px-2">תאריך</th>
                        <th className="text-right py-1 px-2">תיאור</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {forecast.future_receipts.map((r: any, i: number) => (
                        <tr key={i}>
                          <td className="py-1.5 px-2 font-medium">{r.buyer_name}</td>
                          <td className="py-1.5 px-2 text-left text-green-600 font-medium">{formatCurrency(r.amount)}</td>
                          <td className="py-1.5 px-2 text-gray-600">{formatDate(r.date)}</td>
                          <td className="py-1.5 px-2 text-gray-500">{r.description || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="ממתינים לאישור" value={summary.pending_count} sub={formatCurrency(summary.total_pending_amount)} color="amber" />
          <StatCard label="מאושרים" value={summary.approved_count} sub={formatCurrency(summary.total_approved_amount)} color="green" />
          <StatCard label="שולמו (matched)" value={summary.paid_count} sub={formatCurrency(summary.total_paid_amount)} color="blue" />
          <StatCard label='סה"כ' value={summary.total_checks} color="gray" />
        </div>
      )}

      {/* Budget alerts */}
      {summary?.budget_alerts && summary.budget_alerts.length > 0 && (
        <div className="space-y-2">
          {summary.budget_alerts.map((alert, i) => (
            <div key={i} className={`flex items-start gap-2 p-3 rounded-xl text-sm ${
              alert.severity === "error" ? "bg-red-50 border border-red-200 text-red-800" : "bg-amber-50 border border-amber-200 text-amber-800"
            }`}>
              <AlertTriangle size={16} className="shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">{alert.message}</p>
                <p className="text-xs mt-0.5 opacity-70">יתרה נותרת: {formatCurrency(alert.remaining)}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Checks table */}
      {checks.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 bg-gray-50 border-b">
                  <th className="text-right px-3 py-3 font-medium">#</th>
                  <th className="text-right px-3 py-3 font-medium">סוג</th>
                  <th className="text-right px-3 py-3 font-medium">מוטב</th>
                  <th className="text-right px-3 py-3 font-medium">פירוט</th>
                  <th className="text-right px-3 py-3 font-medium">סעיף</th>
                  <th className="text-left px-3 py-3 font-medium">סכום כולל מע&quot;מ</th>
                  <th className="text-right px-3 py-3 font-medium">תאריך</th>
                  <th className="text-center px-3 py-3 font-medium">אישור</th>
                  <th className="text-center px-3 py-3 font-medium">תשלום</th>
                  <th className="w-20 px-3 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {checks.map((c) => (
                  <tr key={c.id} className={`hover:bg-gray-50/50 transition ${
                    c.payment_status === "paid" ? "bg-blue-50/20" : c.approval_status === "rejected" ? "bg-red-50/20" : ""
                  }`}>
                    <td className="px-3 py-3 text-gray-500">{c.serial_number}</td>
                    <td className="px-3 py-3">
                      <span className="text-xs">{c.operation_type === "check" ? "שיק" : "העברה"}</span>
                    </td>
                    <td className="px-3 py-3 font-medium text-gray-900">{c.beneficiary_name}</td>
                    <td className="px-3 py-3 text-gray-600 max-w-[150px] truncate">{c.description || "—"}</td>
                    <td className="px-3 py-3 text-gray-600 text-xs">{c.budget_category || "—"}</td>
                    <td className="px-3 py-3 text-left font-medium">{formatCurrency(c.amount_with_vat)}</td>
                    <td className="px-3 py-3 text-gray-600">{c.due_date ? formatDate(c.due_date) : "—"}</td>
                    <td className="px-3 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${STATUS_COLORS[c.approval_status]}`}>
                        {STATUS_LABELS[c.approval_status]}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${PAYMENT_COLORS[c.payment_status]}`}>
                        {c.payment_status === "paid" ? (
                          <span className="flex items-center gap-1"><Link2 size={10} /> שולם</span>
                        ) : PAYMENT_LABELS[c.payment_status]}
                      </span>
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-1">
                        {c.approval_status === "pending" && (
                          <>
                            <button
                              onClick={() => approveMutation.mutate({ checkId: c.id, status: "approved" })}
                              className="text-gray-400 hover:text-green-600 transition p-1"
                              title="אשר"
                            >
                              <ThumbsUp size={14} />
                            </button>
                            <button
                              onClick={() => approveMutation.mutate({ checkId: c.id, status: "rejected" })}
                              className="text-gray-400 hover:text-red-500 transition p-1"
                              title="דחה"
                            >
                              <ThumbsDown size={14} />
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => deleteMutation.mutate(c.id)}
                          className="text-gray-300 hover:text-red-500 transition p-1"
                          title="מחק"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {checks.length === 0 && !uploading && (
        <div className="text-center py-8 text-gray-400">
          <CreditCard size={40} className="mx-auto mb-3 opacity-50" />
          <p>טרם הועלו שיקים לחודש זה</p>
          <p className="text-sm mt-1">העלה קובץ Excel עם טאב חודשי</p>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/guarantees`)}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition"
        >
          <ChevronRight size={18} /> חזרה לערבויות
        </button>
        <button
          onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/review`)}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition"
        >
          המשך לסקירה <ChevronLeft size={18} />
        </button>
      </div>
    </div>
  );
}

function StatCard({ label, value, sub, color }: { label: string; value: number; sub?: string; color: string }) {
  const colors: Record<string, string> = {
    amber: "bg-amber-50 border-amber-200",
    green: "bg-green-50 border-green-200",
    blue: "bg-blue-50 border-blue-200",
    gray: "bg-gray-50 border-gray-200",
  };
  return (
    <div className={`rounded-xl border p-4 text-center ${colors[color]}`}>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}
