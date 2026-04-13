"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, CheckCircle2, XCircle, AlertTriangle, ClipboardCheck } from "lucide-react";
import api from "@/lib/api";

interface DataCompleteness {
  bank_statement_uploaded: boolean;
  all_transactions_classified: boolean;
  construction_progress_entered: boolean;
  index_updated: boolean;
  ready_to_generate: boolean;
  missing_items: string[];
}

export default function ReviewStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();

  const { data: completeness } = useQuery<DataCompleteness>({
    queryKey: ["completeness", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/completeness`)).data,
  });

  const checks = completeness ? [
    { label: "תדפיס בנק הועלה", done: completeness.bank_statement_uploaded },
    { label: "כל התנועות מסווגות", done: completeness.all_transactions_classified },
    { label: "התקדמות בנייה הוזנה", done: completeness.construction_progress_entered },
    { label: "מדד תשומות עודכן", done: completeness.index_updated },
  ] : [];

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-2xl border border-gray-200 p-8">
        <div className="flex items-center gap-3 mb-6">
          <ClipboardCheck size={24} className="text-primary" />
          <h2 className="text-lg font-bold text-gray-900">סקירה ובדיקת שלמות</h2>
        </div>

        {/* Checklist */}
        <div className="space-y-3 mb-6">
          {checks.map((check, i) => (
            <div key={i} className={`flex items-center gap-3 p-4 rounded-xl ${
              check.done ? "bg-green-50" : "bg-red-50"
            }`}>
              {check.done ? (
                <CheckCircle2 size={22} className="text-green-600 shrink-0" />
              ) : (
                <XCircle size={22} className="text-red-500 shrink-0" />
              )}
              <span className={`font-medium ${check.done ? "text-green-800" : "text-red-800"}`}>
                {check.label}
              </span>
            </div>
          ))}
        </div>

        {/* Missing items warning */}
        {completeness && completeness.missing_items.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle size={18} className="text-amber-600" />
              <span className="font-bold text-amber-800">פריטים חסרים:</span>
            </div>
            <ul className="list-disc list-inside text-sm text-amber-700 space-y-1">
              {completeness.missing_items.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Ready state */}
        {completeness?.ready_to_generate && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
            <CheckCircle2 size={40} className="mx-auto text-green-600 mb-2" />
            <p className="text-green-800 font-bold text-lg">כל הנתונים מלאים!</p>
            <p className="text-green-600 text-sm">ניתן להמשיך להפקת הדוח</p>
          </div>
        )}
      </div>

      <div className="flex justify-between mt-6">
        <button onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/guarantees`)}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition">
          <ChevronRight size={18} /> חזרה
        </button>
        <button
          onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/generate`)}
          disabled={!completeness?.ready_to_generate}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          המשך להפקת דוח <ChevronLeft size={18} />
        </button>
      </div>
    </div>
  );
}
