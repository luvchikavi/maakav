"use client";

import { useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Upload, CheckCircle, ChevronLeft, AlertTriangle } from "lucide-react";
import api from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/formatters";

interface Transaction {
  id: number;
  transaction_date: string;
  description: string;
  amount: number;
  balance: number | null;
  transaction_type: string;
  category: string | null;
  ai_suggested_category: string | null;
  is_manually_classified: boolean;
}

const EXPENSE_CATEGORIES = [
  { value: "tenant_expenses", label: "הוצאות דיירים" },
  { value: "land_and_taxes", label: "קרקע ומיסוי" },
  { value: "indirect_costs", label: "הוצאות עקיפות" },
  { value: "direct_construction", label: "בניה ישירה" },
  { value: "deposit_to_savings", label: "הפקדה לפקדון" },
  { value: "other_expense", label: "הוצאה אחרת" },
  { value: "loan_repayment", label: "החזר הלוואה" },
  { value: "interest_and_fees", label: "ריביות ועמלות" },
];

const INCOME_CATEGORIES = [
  { value: "sale_income", label: "הכנסה ממכירה" },
  { value: "tax_refunds", label: "החזרי מיסים" },
  { value: "vat_refunds", label: 'החזרי מע"מ' },
  { value: "equity_deposit", label: "הפקדת הון עצמי" },
  { value: "loan_received", label: "הכנסה מהלוואה" },
  { value: "other_income", label: "הכנסה אחרת" },
];

export default function BankStatementStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ transactions_count: number; bank_name: string } | null>(null);

  const { data: transactions = [], isLoading } = useQuery<Transaction[]>({
    queryKey: ["transactions", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/transactions`)).data,
  });

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post(
        `/projects/${projectId}/monthly-reports/${reportId}/bank-statements/upload`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setUploadResult({ transactions_count: data.transactions_count, bank_name: data.bank_name || "" });
      queryClient.invalidateQueries({ queryKey: ["transactions", reportId] });
      queryClient.invalidateQueries({ queryKey: ["completeness", reportId] });
    } catch (err: any) {
      alert(err?.response?.data?.detail || "שגיאה בהעלאת הקובץ");
    } finally {
      setUploading(false);
    }
  }, [projectId, reportId, queryClient]);

  const classifyMutation = useMutation({
    mutationFn: async ({ txId, category }: { txId: number; category: string }) => {
      return api.patch(`/projects/${projectId}/monthly-reports/${reportId}/transactions/${txId}`, { category });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions", reportId] });
      queryClient.invalidateQueries({ queryKey: ["completeness", reportId] });
    },
  });

  const unclassifiedCount = transactions.filter((t) => !t.category).length;
  const totalCredits = transactions.filter((t) => t.transaction_type === "credit").reduce((s, t) => s + Number(t.amount), 0);
  const totalDebits = transactions.filter((t) => t.transaction_type === "debit").reduce((s, t) => s + Number(t.amount), 0);

  return (
    <div>
      {/* Upload zone */}
      {transactions.length === 0 && (
        <div
          className="bg-white rounded-2xl border-2 border-dashed border-gray-200 hover:border-primary/40 p-12 text-center mb-6 cursor-pointer transition"
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
              <p className="text-gray-600 font-medium">AI מפרסר את התדפיס...</p>
              <p className="text-gray-400 text-sm">זה עשוי לקחת כ-30 שניות</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <Upload size={48} className="text-gray-400" />
              <p className="text-gray-700 font-medium text-lg">העלה תדפיס בנק</p>
              <p className="text-gray-400">PDF או Excel - המערכת תפרסר אוטומטית</p>
            </div>
          )}
        </div>
      )}

      {/* Upload result */}
      {uploadResult && (
        <div className="bg-green-50 rounded-2xl border border-green-200 p-4 mb-6 flex items-center gap-3">
          <CheckCircle size={24} className="text-green-600 shrink-0" />
          <div>
            <p className="text-green-800 font-medium">
              פורסרו {uploadResult.transactions_count} תנועות {uploadResult.bank_name ? `מ${uploadResult.bank_name}` : ""}
            </p>
            <p className="text-green-600 text-sm">סווג כל תנועה בטבלה למטה</p>
          </div>
        </div>
      )}

      {/* Summary stats */}
      {transactions.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-2xl border border-gray-200 p-4 text-center">
            <p className="text-sm text-gray-500">סה&quot;כ זכות</p>
            <p className="text-xl font-bold text-green-600">{formatCurrency(totalCredits)}</p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-200 p-4 text-center">
            <p className="text-sm text-gray-500">סה&quot;כ חובה</p>
            <p className="text-xl font-bold text-red-600">{formatCurrency(totalDebits)}</p>
          </div>
          <div className={`rounded-2xl border p-4 text-center ${
            unclassifiedCount > 0 ? "bg-amber-50 border-amber-200" : "bg-green-50 border-green-200"
          }`}>
            <p className="text-sm text-gray-500">לא מסווגות</p>
            <p className={`text-xl font-bold ${unclassifiedCount > 0 ? "text-amber-600" : "text-green-600"}`}>
              {unclassifiedCount}
            </p>
          </div>
        </div>
      )}

      {/* Transaction table */}
      {transactions.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-500 bg-gray-50 border-b">
                  <th className="text-right px-4 py-3 font-medium">תאריך</th>
                  <th className="text-right px-4 py-3 font-medium">תיאור</th>
                  <th className="text-left px-4 py-3 font-medium">סכום</th>
                  <th className="text-left px-4 py-3 font-medium">יתרה</th>
                  <th className="text-right px-4 py-3 font-medium w-52">סיווג</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {transactions.map((tx) => (
                  <tr key={tx.id} className={`hover:bg-gray-50/50 transition ${!tx.category ? "bg-amber-50/30" : ""}`}>
                    <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">{formatDate(tx.transaction_date)}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate">{tx.description}</td>
                    <td className={`px-4 py-3 text-sm font-medium text-left whitespace-nowrap ${
                      tx.transaction_type === "credit" ? "text-green-600" : "text-red-600"
                    }`}>
                      {tx.transaction_type === "credit" ? "+" : "-"}{formatCurrency(Number(tx.amount))}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 text-left whitespace-nowrap">
                      {tx.balance ? formatCurrency(Number(tx.balance)) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={tx.category || ""}
                        onChange={(e) => {
                          if (e.target.value) {
                            classifyMutation.mutate({ txId: tx.id, category: e.target.value });
                          }
                        }}
                        className={`w-full px-3 py-1.5 rounded-lg border text-xs ${
                          tx.category
                            ? "border-green-200 bg-green-50 text-green-800"
                            : "border-amber-200 bg-amber-50 text-amber-800"
                        } focus:outline-none focus:ring-2 focus:ring-primary/20`}
                      >
                        <option value="">— בחר סיווג —</option>
                        <optgroup label="הוצאות">
                          {EXPENSE_CATEGORIES.map((c) => (
                            <option key={c.value} value={c.value}>{c.label}</option>
                          ))}
                        </optgroup>
                        <optgroup label="הכנסות">
                          {INCOME_CATEGORIES.map((c) => (
                            <option key={c.value} value={c.value}>{c.label}</option>
                          ))}
                        </optgroup>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Next step */}
      {transactions.length > 0 && (
        <div className="flex justify-between mt-6">
          <div />
          <button
            onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/sales`)}
            className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition"
          >
            המשך למכירות
            <ChevronLeft size={18} />
          </button>
        </div>
      )}
    </div>
  );
}
