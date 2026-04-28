"use client";

import { useState, useCallback, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft, ChevronRight, Shield, Upload, CheckCircle, AlertTriangle,
  Trash2, Plus, Save, RotateCcw,
} from "lucide-react";
import api from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/formatters";
import NumberInput from "@/components/ui/NumberInput";

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

const GUARANTEE_TYPES: { value: string; label: string }[] = [
  { value: "sale_law", label: "חוק מכר" },
  { value: "performance", label: "ביצוע" },
  { value: "financial", label: "כספית" },
  { value: "bank", label: "בנקאית" },
  { value: "other", label: "אחר" },
];

const TYPE_COLORS: Record<string, string> = {
  sale_law: "bg-blue-100 text-blue-700 border-blue-200",
  performance: "bg-purple-100 text-purple-700 border-purple-200",
  financial: "bg-amber-100 text-amber-700 border-amber-200",
  bank: "bg-green-100 text-green-700 border-green-200",
  other: "bg-gray-100 text-gray-700 border-gray-200",
};

const blankItem = (): GuaranteeItem => ({
  buyer_name: "",
  guarantee_type: "sale_law",
  original_amount: 0,
  indexed_balance: 0,
  expiry_date: null,
  apartment_number: "",
  notes: "",
});

const itemsEqual = (a: GuaranteeItem[], b: GuaranteeItem[]): boolean => {
  if (a.length !== b.length) return false;
  return JSON.stringify(a) === JSON.stringify(b);
};

export default function GuaranteesStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ items_count: number; warnings: string[] } | null>(null);
  const [draft, setDraft] = useState<GuaranteeItem[]>([]);

  const { data: guarantees } = useQuery<GuaranteeData>({
    queryKey: ["guarantees", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/guarantees`)).data,
  });

  const items = guarantees?.items || [];

  // Sync draft from server whenever it changes (after upload, after save).
  useEffect(() => {
    setDraft(items.map((i) => ({ ...i })));
  }, [guarantees]);

  const dirty = !itemsEqual(items, draft);

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
      const detail = err?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "שגיאה בהעלאת הקובץ");
    } finally {
      setUploading(false);
    }
  }, [projectId, reportId, qc]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      await api.put(
        `/projects/${projectId}/monthly-reports/${reportId}/guarantees/items`,
        { items: draft },
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["guarantees", reportId] });
      qc.invalidateQueries({ queryKey: ["guarantee-validation", reportId] });
      qc.invalidateQueries({ queryKey: ["completeness", reportId] });
    },
  });

  const updateRow = (idx: number, patch: Partial<GuaranteeItem>) => {
    setDraft((prev) => prev.map((row, i) => (i === idx ? { ...row, ...patch } : row)));
  };
  const removeRow = (idx: number) => {
    setDraft((prev) => prev.filter((_, i) => i !== idx));
  };
  const addRow = () => {
    setDraft((prev) => [...prev, blankItem()]);
  };
  const resetDraft = () => {
    setDraft(items.map((i) => ({ ...i })));
  };

  const totalBalance = draft.reduce((s, i) => s + (Number(i.indexed_balance) || 0), 0);
  const saleLawCount = draft.filter((i) => i.guarantee_type === "sale_law").length;
  const saleLawTotal = draft
    .filter((i) => i.guarantee_type === "sale_law")
    .reduce((s, i) => s + (Number(i.indexed_balance) || 0), 0);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
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

        {uploadResult && (
          <div className="mt-4">
            <div className="bg-blue-50 rounded-xl border border-blue-200 p-4 flex items-center gap-3">
              <CheckCircle size={20} className="text-blue-600 shrink-0" />
              <div className="text-sm text-blue-900">
                <p className="font-medium">זוהו {uploadResult.items_count} ערבויות</p>
                <p className="text-xs mt-0.5">קריאת ה-OCR אינה מושלמת — בדוק כל שורה ותקן שמות/סכומים לפני שמירה.</p>
              </div>
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
      {draft.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-2xl border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-gray-900">{draft.length}</p>
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

      {/* Editable items table */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-bold text-gray-900">סקירה ועריכה</span>
            <span className="text-gray-400">— ניתן לתקן כל שדה אחרי קריאת ה-OCR</span>
          </div>
          <div className="flex items-center gap-2">
            {dirty && (
              <button
                onClick={resetDraft}
                disabled={saveMutation.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 rounded-lg transition disabled:opacity-50"
                title="בטל שינויים"
              >
                <RotateCcw size={14} /> בטל
              </button>
            )}
            <button
              onClick={() => saveMutation.mutate()}
              disabled={!dirty || saveMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-white rounded-lg hover:bg-primary-dark transition disabled:opacity-50"
            >
              <Save size={14} />
              {saveMutation.isPending ? "שומר..." : dirty ? "שמור שינויים" : "נשמר"}
            </button>
          </div>
        </div>

        {draft.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">
            אין ערבויות מתועדות. ניתן להעלות תדפיס למעלה או להוסיף ידנית.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-500 bg-gray-50 border-b">
                  <th className="text-right px-3 py-2 font-medium min-w-[180px]">מוטב</th>
                  <th className="text-center px-3 py-2 font-medium w-32">סוג</th>
                  <th className="text-right px-3 py-2 font-medium w-24">דירה</th>
                  <th className="text-left px-3 py-2 font-medium w-36">סכום מקורי</th>
                  <th className="text-left px-3 py-2 font-medium w-36">יתרה צמודה</th>
                  <th className="text-right px-3 py-2 font-medium w-36">תוקף</th>
                  <th className="text-right px-3 py-2 font-medium min-w-[140px]">הערות</th>
                  <th className="w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {draft.map((row, idx) => (
                  <tr key={idx} className="hover:bg-gray-50/50 transition">
                    <td className="px-3 py-2">
                      <input
                        type="text"
                        value={row.buyer_name}
                        onChange={(e) => updateRow(idx, { buyer_name: e.target.value })}
                        placeholder="שם רוכש / מוטב"
                        className="w-full px-2 py-1 rounded-lg border border-transparent hover:border-gray-200 focus:border-primary focus:bg-white text-sm focus:outline-none focus:ring-1 focus:ring-primary/20"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <select
                        value={row.guarantee_type}
                        onChange={(e) => updateRow(idx, { guarantee_type: e.target.value })}
                        className={`w-full px-2 py-1 rounded-lg border text-xs font-medium ${TYPE_COLORS[row.guarantee_type] || TYPE_COLORS.other} focus:outline-none focus:ring-2 focus:ring-primary/20`}
                      >
                        {GUARANTEE_TYPES.map((t) => (
                          <option key={t.value} value={t.value}>{t.label}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="text"
                        value={row.apartment_number}
                        onChange={(e) => updateRow(idx, { apartment_number: e.target.value })}
                        placeholder="—"
                        className="w-full px-2 py-1 rounded-lg border border-transparent hover:border-gray-200 focus:border-primary focus:bg-white text-sm focus:outline-none focus:ring-1 focus:ring-primary/20"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <NumberInput
                        value={row.original_amount}
                        onChange={(v) => updateRow(idx, { original_amount: Number(v) || 0 })}
                        className="w-full px-2 py-1 rounded-lg border border-transparent hover:border-gray-200 focus:border-primary focus:bg-white text-sm text-left focus:outline-none focus:ring-1 focus:ring-primary/20"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <NumberInput
                        value={row.indexed_balance}
                        onChange={(v) => updateRow(idx, { indexed_balance: Number(v) || 0 })}
                        className="w-full px-2 py-1 rounded-lg border border-transparent hover:border-gray-200 focus:border-primary focus:bg-white text-sm font-medium text-left focus:outline-none focus:ring-1 focus:ring-primary/20"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="date"
                        value={row.expiry_date || ""}
                        onChange={(e) => updateRow(idx, { expiry_date: e.target.value || null })}
                        dir="ltr"
                        className="w-full px-2 py-1 rounded-lg border border-transparent hover:border-gray-200 focus:border-primary focus:bg-white text-sm focus:outline-none focus:ring-1 focus:ring-primary/20"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="text"
                        value={row.notes || ""}
                        onChange={(e) => updateRow(idx, { notes: e.target.value })}
                        placeholder="הערות"
                        className="w-full px-2 py-1 rounded-lg border border-transparent hover:border-gray-200 focus:border-primary focus:bg-white text-sm focus:outline-none focus:ring-1 focus:ring-primary/20"
                      />
                    </td>
                    <td className="px-3 py-2 text-center">
                      <button
                        onClick={() => removeRow(idx)}
                        className="text-gray-300 hover:text-red-500 transition"
                        title="הסר שורה"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="px-4 py-3 border-t border-gray-100 flex justify-between items-center">
          <button
            onClick={addRow}
            className="flex items-center gap-1.5 text-sm text-primary hover:text-primary-dark transition"
          >
            <Plus size={14} /> הוסף ערבות ידנית
          </button>
          {dirty && (
            <span className="text-xs text-amber-600 font-medium">יש שינויים שלא נשמרו</span>
          )}
        </div>
      </div>

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
