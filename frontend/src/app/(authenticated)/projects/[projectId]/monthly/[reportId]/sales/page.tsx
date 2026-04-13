"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, ShoppingCart } from "lucide-react";
import api from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/formatters";

export default function SalesStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();

  const { data: summary } = useQuery({
    queryKey: ["sales-summary", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/sales/summary`)).data,
  });

  return (
    <div className="max-w-3xl mx-auto">
      <div className="bg-white rounded-2xl border border-gray-200 p-8">
        <h2 className="text-lg font-bold text-gray-900 mb-6">סיכום מכירות</h2>

        {summary ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <StatCard label='סה"כ יח"ד יזם' value={String(summary.total_units_developer)} />
            <StatCard label="נמכרו" value={String(summary.total_sold)} sub={formatPercent(summary.sold_percent)} />
            <StatCard label="מוכרות (>15%)" value={String(summary.recognized_by_bank)} sub={formatPercent(summary.recognized_percent)} />
            <StatCard label="למכירה" value={String(summary.unsold)} />
          </div>
        ) : (
          <div className="text-center py-8">
            <ShoppingCart size={40} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500">טרם הוזנו נתוני מכירות</p>
          </div>
        )}

        <p className="text-sm text-gray-500 bg-gray-50 rounded-xl p-4">
          מכירות חדשות ניתן להזין דרך עמוד הפרויקט. שלב זה מציג סיכום בלבד.
          בשלב הבא אנו נתמוך בהזנת מכירות חדשות ישירות מהמעקב החודשי.
        </p>
      </div>

      <div className="flex justify-between mt-6">
        <button onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/bank-statement`)}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition">
          <ChevronRight size={18} /> חזרה לתדפיס בנק
        </button>
        <button onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/construction`)}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition">
          המשך להתקדמות בנייה <ChevronLeft size={18} />
        </button>
      </div>
    </div>
  );
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-50 rounded-xl p-4 text-center">
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
      {sub && <p className="text-xs text-primary font-medium mt-0.5">{sub}</p>}
    </div>
  );
}
