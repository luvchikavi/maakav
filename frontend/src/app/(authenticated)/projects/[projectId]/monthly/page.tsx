"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Plus, FileText, CheckCircle2, Clock, Lock } from "lucide-react";
import api from "@/lib/api";
import { formatDate, formatMonthYear } from "@/lib/formatters";

interface MonthlyReport {
  id: number;
  report_month: string;
  report_number: number;
  status: string;
  generated_at: string | null;
  created_at: string;
}

const STATUS_CONFIG: Record<string, { label: string; icon: typeof Clock; color: string }> = {
  draft: { label: "טיוטה", icon: Clock, color: "text-gray-500 bg-gray-50" },
  data_entry: { label: "בהזנה", icon: FileText, color: "text-blue-600 bg-blue-50" },
  review: { label: "בסקירה", icon: FileText, color: "text-amber-600 bg-amber-50" },
  approved: { label: "מאושר", icon: CheckCircle2, color: "text-green-600 bg-green-50" },
  locked: { label: "נעול", icon: Lock, color: "text-gray-600 bg-gray-100" },
};

export default function MonthlyReportsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [month, setMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
  });

  const { data: reports = [], isLoading } = useQuery<MonthlyReport[]>({
    queryKey: ["monthly-reports", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports`)).data,
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      return api.post(`/projects/${projectId}/monthly-reports`, { report_month: month });
    },
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["monthly-reports", projectId] });
      router.push(`/projects/${projectId}/monthly/${res.data.id}/bank-statement`);
    },
  });

  return (
    <div>
      <button onClick={() => router.push(`/projects/${projectId}`)} className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4 transition">
        <ArrowRight size={18} /> חזרה לפרויקט
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">דוחות מעקב חודשיים</h1>
          <p className="text-gray-500 mt-1">{reports.length} דוחות</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition"
        >
          <Plus size={18} /> דוח חדש
        </button>
      </div>

      {/* Create dialog */}
      {showCreate && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-6">
          <h3 className="font-bold text-gray-900 mb-4">יצירת דוח חודשי חדש</h3>
          <div className="flex items-end gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1.5">חודש הדוח</label>
              <input
                type="month"
                value={month.slice(0, 7)}
                onChange={(e) => setMonth(`${e.target.value}-01`)}
                dir="ltr"
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
            </div>
            <button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
              className="px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition disabled:opacity-50"
            >
              {createMutation.isPending ? "יוצר..." : "צור דוח"}
            </button>
            <button onClick={() => setShowCreate(false)} className="px-4 py-3 text-gray-500 hover:text-gray-700 transition">
              ביטול
            </button>
          </div>
          {createMutation.isError && (
            <p className="text-red-600 text-sm mt-2">
              {(createMutation.error as any)?.response?.data?.detail || "שגיאה ביצירת הדוח"}
            </p>
          )}
        </div>
      )}

      {/* Reports list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : reports.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center">
          <FileText size={48} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500">טרם נוצרו דוחות. לחץ &quot;דוח חדש&quot; להתחיל.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((report) => {
            const statusCfg = STATUS_CONFIG[report.status] || STATUS_CONFIG.draft;
            const StatusIcon = statusCfg.icon;

            return (
              <button
                key={report.id}
                onClick={() => router.push(`/projects/${projectId}/monthly/${report.id}/bank-statement`)}
                className="w-full flex items-center justify-between bg-white rounded-2xl border border-gray-200 p-5 hover:shadow-md transition text-right"
              >
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-xl bg-primary/10 text-primary flex items-center justify-center text-xl font-bold">
                    {report.report_number}
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900">דוח מס&apos; {report.report_number}</h3>
                    <p className="text-sm text-gray-500">{formatMonthYear(report.report_month)}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${statusCfg.color}`}>
                    <StatusIcon size={14} />
                    {statusCfg.label}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
