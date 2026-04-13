"use client";

import { useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Upload, Plus, Trash2, FileSpreadsheet, CheckCircle } from "lucide-react";
import api from "@/lib/api";
import { formatCurrency } from "@/lib/formatters";

interface BudgetLineItem {
  id: number;
  line_number: number;
  description: string;
  source: string | null;
  cost_no_vat: number;
  is_index_linked: boolean;
  supplier_name: string | null;
  notes: string | null;
}

interface BudgetCategory {
  id: number;
  category_type: string;
  display_order: number;
  total_amount: number;
  line_items: BudgetLineItem[];
}

const CATEGORY_LABELS: Record<string, string> = {
  tenant_expenses: "קרקע והוצאות דיירים",
  land_and_taxes: "קרקע ומיסוי",
  indirect_costs: "כלליות",
  direct_construction: "בניה ישירה (הקמה)",
  extraordinary: "הוצאות חריגות",
};

export default function BudgetSetupPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ items_count: number; total_budget: number } | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const { data: categories = [], isLoading } = useQuery<BudgetCategory[]>({
    queryKey: ["budget", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/setup/budget`)).data,
  });

  const handleFileUpload = useCallback(async (file: File) => {
    if (!file.name.match(/\.xlsx?$/i)) {
      alert("נדרש קובץ Excel (.xlsx)");
      return;
    }
    setUploading(true);
    setUploadResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post(`/projects/${projectId}/setup/budget/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadResult({ items_count: data.items_count, total_budget: data.total_budget });
      queryClient.invalidateQueries({ queryKey: ["budget", projectId] });
      queryClient.invalidateQueries({ queryKey: ["setup-status", projectId] });
    } catch (err: any) {
      alert(err?.response?.data?.detail || "שגיאה בהעלאת הקובץ");
    } finally {
      setUploading(false);
    }
  }, [projectId, queryClient]);

  const totalBudget = categories.reduce((sum, c) => sum + Number(c.total_amount), 0);
  const totalItems = categories.reduce((sum, c) => sum + c.line_items.length, 0);

  return (
    <div>
      <button onClick={() => router.push(`/projects/${projectId}`)} className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4 transition">
        <ArrowRight size={18} /> חזרה לפרויקט
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">תקציב הפרויקט (סעיף 8)</h1>
          <p className="text-gray-500 mt-1">תקציב מקורי מדוח האפס - T1</p>
        </div>
        {totalItems > 0 && (
          <div className="text-left bg-primary/5 rounded-xl px-5 py-3">
            <p className="text-sm text-gray-500">{totalItems} סעיפים</p>
            <p className="text-xl font-bold text-primary">{formatCurrency(totalBudget)}</p>
          </div>
        )}
      </div>

      {/* Upload Zone */}
      <div
        onDragEnter={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={(e) => { e.preventDefault(); setDragActive(false); }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          if (e.dataTransfer.files[0]) handleFileUpload(e.dataTransfer.files[0]);
        }}
        className={`bg-white rounded-2xl border-2 border-dashed p-8 text-center mb-6 transition cursor-pointer ${
          dragActive ? "border-primary bg-primary/5" : "border-gray-200 hover:border-primary/40"
        }`}
        onClick={() => {
          const input = document.createElement("input");
          input.type = "file";
          input.accept = ".xlsx,.xls";
          input.onchange = (e) => {
            const file = (e.target as HTMLInputElement).files?.[0];
            if (file) handleFileUpload(file);
          };
          input.click();
        }}
      >
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-600">מעבד את הקובץ...</p>
          </div>
        ) : uploadResult ? (
          <div className="flex flex-col items-center gap-2">
            <CheckCircle size={40} className="text-green-500" />
            <p className="text-green-700 font-medium">יובאו {uploadResult.items_count} סעיפים</p>
            <p className="text-gray-500">סה&quot;כ תקציב: {formatCurrency(uploadResult.total_budget)}</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload size={40} className="text-gray-400" />
            <p className="text-gray-700 font-medium">גרור קובץ Excel לכאן או לחץ לבחירה</p>
            <p className="text-gray-400 text-sm">הקובץ צריך לכלול: קטגוריה, סעיף, עלות ללא מע&quot;מ</p>
          </div>
        )}
      </div>

      {/* Budget Table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : categories.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center">
          <FileSpreadsheet size={48} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500">טרם הועלה תקציב. העלה קובץ Excel או הזן ידנית.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {categories.map((category) => (
            <div key={category.id} className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
              {/* Category Header */}
              <div className="px-6 py-4 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
                <h3 className="font-bold text-gray-900">
                  {CATEGORY_LABELS[category.category_type] || category.category_type}
                </h3>
                <span className="text-sm font-bold text-primary">{formatCurrency(Number(category.total_amount))}</span>
              </div>

              {/* Line Items */}
              <table className="w-full">
                <thead>
                  <tr className="text-xs text-gray-500 border-b border-gray-50">
                    <th className="text-right px-6 py-2 font-medium">#</th>
                    <th className="text-right px-4 py-2 font-medium">סעיף</th>
                    <th className="text-right px-4 py-2 font-medium">ספק</th>
                    <th className="text-left px-6 py-2 font-medium">עלות ללא מע&quot;מ</th>
                    <th className="text-center px-4 py-2 font-medium">צמוד</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {category.line_items.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-50/50 transition">
                      <td className="px-6 py-3 text-sm text-gray-400">{item.line_number}</td>
                      <td className="px-4 py-3 text-sm text-gray-900">{item.description}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{item.supplier_name || "—"}</td>
                      <td className="px-6 py-3 text-sm text-gray-900 text-left font-medium">
                        {formatCurrency(Number(item.cost_no_vat))}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`text-xs ${item.is_index_linked ? "text-green-600" : "text-gray-400"}`}>
                          {item.is_index_linked ? "כן" : "לא"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}

          {/* Total */}
          <div className="bg-primary/5 rounded-2xl p-6 flex items-center justify-between">
            <span className="text-lg font-bold text-gray-900">סה&quot;כ תקציב פרויקט</span>
            <span className="text-2xl font-bold text-primary">{formatCurrency(totalBudget)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
