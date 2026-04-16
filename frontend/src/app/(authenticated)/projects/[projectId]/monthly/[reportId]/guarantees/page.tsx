"use client";

import { useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft, ChevronRight, Shield, Upload, CheckCircle, AlertTriangle, Trash2,
} from "lucide-react";
import api from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/formatters";

interface GuaranteeItem {
  buyer_name: string;
  guarantee_type: string;
  original_amount: number;
  indexed_balance: number;
  expiry_date: string | null;
  apartment_number: string;
  notes: string;
}

interface GuaranteeData {
  id?: number;
  items: GuaranteeItem[];
  total_balance: number;
  total_receipts: number;
  gap: number;
  notes: string | null;
}

const TYPE_LABELS: Record<string, string> = {
  sale_law: "חוק מכר",
  performance: "ביצוע",
  financial: "כספית",
  bank: "בנקאית",
  other: "אחר",
};

const TYPE_COLORS: Record<string, string> = {
  sale_law: "bg-blue-100 text-blue-700",
  performance: "bg-purple-100 text-purple-700",
  financial: "bg-amber-100 text-amber-700",
  bank: "bg-green-100 text-green-700",
  other: "bg-gray-100 text-gray-700",
};

export default function GuaranteesStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ items_count: number; warnings: string[] } | null>(null);

  const { data: guarantees } = useQuery<GuaranteeData>({
    queryKey: ["guarantees", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/guarantees`)).data,
  });

  const items = guarantees?.items || [];

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setUploadResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post(
        `/projects/${projectId}/monthly-reports/${reportId}/guarantees/upload`,
        formData,
      );
      setUploadResult({ items_count: data.items_count, warnings: data.warnings || [] });
      qc.invalidateQueries({ queryKey: ["guarantees", reportId] });
      qc.invalidateQueries({ queryKey: ["completeness", reportId] });
    } catch (err: any) {
      alert(err?.response?.data?.detail || "שגיאה בהעלאת הקובץ");
    } finally {
      setUploading(false);
    }
  }, [projectId, reportId, qc]);

  const deleteItemMutation = useMutation({
    mutationFn: async (index: number) => {
      const updated = [...items];
      updated.splice(index, 1);
      await api.put(`/projects/${projectId}/monthly-reports/${reportId}/guarantees/items`, { items: updated });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["guarantees", reportId] }),
  });

  const totalBalance = items.reduce((s, i) => s + (i.indexed_balance || 0), 0);
  const saleLawCount = items.filter((i) => i.guarantee_type === "sale_law").length;
  const saleLawTotal = items.filter((i) => i.guarantee_type === "sale_law").reduce((s, i) => s + (i.indexed_balance || 0), 0);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Upload zone */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Shield size={24} className="text-primary" />
          <h2 className="text-lg font-bold text-gray-900">ערבויות</h2>
        </div>

        <div
          className="border-2 border-dashed border-gray-200 hover:border-primary/40 rounded-xl p-8 text-center cursor-pointer transition"
          onClick={() => {
            const input = document.createElement("input");
            input.type = "file";
            input.accept = ".pdf,.xlsx,.xls";
            input.onchange = (e) => {
              const f = (e.target as HTMLInputElement).files?.[0];
              if (f) handleUpload(f);
            };
            input.click();
          }}
        >
          {uploading ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-gray-600 font-medium">מפרסר את תדפיס הערבויות...</p>
              <p className="text-gray-400 text-sm">זה עשוי לקחת מספר שניות</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <Upload size={36} className="text-gray-400" />
              <p className="text-gray-700 font-medium">
                {items.length > 0 ? "העלה תדפיס חדש (יחליף את הקיים)" : "העלה תדפיס ערבויות"}
              </p>
              <p className="text-gray-400 text-sm">PDF או Excel</p>
            </div>
          )}
        </div>

        {/* Upload result */}
        {uploadResult && (
          <div className="mt-4">
            <div className="bg-green-50 rounded-xl border border-green-200 p-4 flex items-center gap-3">
              <CheckCircle size={20} className="text-green-600 shrink-0" />
              <p className="text-green-800 text-sm font-medium">
                זוהו {uploadResult.items_count} ערבויות
              </p>
            </div>
            {uploadResult.warnings.length > 0 && (
              <div className="bg-amber-50 rounded-xl border border-amber-200 p-4 mt-2">
                {uploadResult.warnings.map((w, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-amber-800">
                    <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                    <span>{w}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Summary cards */}
      {items.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-2xl border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-gray-900">{items.length}</p>
            <p className="text-xs text-gray-500">ערבויות</p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-blue-700">{saleLawCount}</p>
            <p className="text-xs text-gray-500">חוק מכר</p>
            <p className="text-xs text-blue-600 mt-0.5">{formatCurrency(saleLawTotal)}</p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-200 p-4 text-center">
            <p className="text-lg font-bold text-gray-900">{formatCurrency(totalBalance)}</p>
            <p className="text-xs text-gray-500">סה&quot;כ יתרת ערבויות</p>
          </div>
        </div>
      )}

      {/* Items table */}
      {items.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-500 bg-gray-50 border-b">
                  <th className="text-right px-4 py-3 font-medium">מוטב</th>
                  <th className="text-center px-4 py-3 font-medium">סוג</th>
                  <th className="text-right px-4 py-3 font-medium">דירה</th>
                  <th className="text-left px-4 py-3 font-medium">סכום מקורי</th>
                  <th className="text-left px-4 py-3 font-medium">יתרה צמודה</th>
                  <th className="text-right px-4 py-3 font-medium">תוקף</th>
                  <th className="w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {items.map((item, idx) => (
                  <tr key={idx} className="hover:bg-gray-50/50 transition">
                    <td className="px-4 py-3 text-sm text-gray-900">{item.buyer_name}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${TYPE_COLORS[item.guarantee_type] || TYPE_COLORS.other}`}>
                        {TYPE_LABELS[item.guarantee_type] || item.guarantee_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{item.apartment_number || "—"}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 text-left">{formatCurrency(item.original_amount)}</td>
                    <td className="px-4 py-3 text-sm font-medium text-left">{formatCurrency(item.indexed_balance)}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{item.expiry_date ? formatDate(item.expiry_date) : "—"}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => deleteItemMutation.mutate(idx)}
                        className="text-gray-400 hover:text-red-500 transition"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/index`)}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition"
        >
          <ChevronRight size={18} /> חזרה
        </button>
        <button
          onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/checks`)}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition"
        >
          המשך לאישורי שיקים <ChevronLeft size={18} />
        </button>
      </div>
    </div>
  );
}
