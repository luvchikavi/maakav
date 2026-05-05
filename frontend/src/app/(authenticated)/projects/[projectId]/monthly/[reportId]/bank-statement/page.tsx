"use client";

import { useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Upload, CheckCircle, ChevronLeft, AlertTriangle, Sparkles, Trash2, Wallet,
  FileText, RefreshCw, Eye,
} from "lucide-react";
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
  category_primary: string | null;
  subcategory: string | null;
  ai_suggested_category: string | null;
  ai_confidence: number | null;
  is_manually_classified: boolean;
}

interface Taxonomy {
  primaries: { key: string; label: string }[];
  secondaries: Record<string, { key: string; label: string }[]>;
  legacy_to_primary: Record<string, string>;
}

const BUDGET_LINE_PRIMARIES = new Set([
  "tenant_expenses", "land_and_taxes", "indirect_costs", "direct_construction",
]);
const EXPENSE_PRIMARIES = new Set([
  "tenant_expenses", "land_and_taxes", "indirect_costs", "direct_construction",
  "interest_fees_guarantees", "withdrawals",
]);

// Old flat category constants were replaced by the primary+secondary
// taxonomy fetched via /transactions/taxonomy.

export default function BankStatementStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{
    transactions_count: number;
    bank_name: string;
    auto_classified: number;
    warnings: string[];
  } | null>(null);
  const [approved, setApproved] = useState(false);
  const [selectedTxIds, setSelectedTxIds] = useState<Set<number>>(new Set());

  const { data: transactions = [] } = useQuery<Transaction[]>({
    queryKey: ["transactions", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/transactions`)).data,
  });

  const { data: taxonomy } = useQuery<Taxonomy>({
    queryKey: ["transaction-taxonomy"],
    queryFn: async () => (await api.get(`/transactions/taxonomy`)).data,
    staleTime: 1000 * 60 * 60, // taxonomy is static, cache for an hour
  });

  // Budget structure — used as the secondary list when primary is one of
  // the four budget-line categories (tenant_expenses / land_and_taxes /
  // indirect_costs / direct_construction).
  type BudgetLine = { id: number; description: string };
  type BudgetCat = { category_type: string; line_items: BudgetLine[] };
  const { data: budgetCategories = [] } = useQuery<BudgetCat[]>({
    queryKey: ["budget", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/setup/budget`)).data,
    staleTime: 1000 * 60 * 5,
  });
  const budgetLinesByCategory = (() => {
    const out: Record<string, BudgetLine[]> = {};
    for (const cat of budgetCategories) out[cat.category_type] = cat.line_items || [];
    return out;
  })();

  // If there are already transactions in DB, consider it approved
  const hasExistingData = transactions.length > 0;

  const handleUpload = useCallback(async (file: File) => {
    setUploadResult(null);
    setApproved(false);
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post(
        `/projects/${projectId}/monthly-reports/${reportId}/bank-statements/upload`,
        formData,
      );
      setUploadResult({
        transactions_count: data.transactions_count,
        bank_name: data.bank_name || "",
        auto_classified: data.auto_classified || 0,
        warnings: data.warnings || [],
      });
      queryClient.invalidateQueries({ queryKey: ["transactions", reportId] });
      queryClient.invalidateQueries({ queryKey: ["completeness", reportId] });
      queryClient.invalidateQueries({ queryKey: ["bank-summary", reportId] });
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "שגיאה בהעלאת הקובץ");
    } finally {
      setUploading(false);
    }
  }, [projectId, reportId, queryClient]);

  const triggerFileSelect = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf,.xlsx,.xls";
    input.onchange = (e) => {
      const f = (e.target as HTMLInputElement).files?.[0];
      if (f) handleUpload(f);
    };
    input.click();
  }, [handleUpload]);

  const handleApprove = () => {
    setApproved(true);
    setUploadResult(null);
  };

  const handleReplace = () => {
    setUploadResult(null);
    setApproved(false);
    triggerFileSelect();
  };

  const invalidateBudgetDependentQueries = () => {
    queryClient.invalidateQueries({ queryKey: ["transactions", reportId] });
    queryClient.invalidateQueries({ queryKey: ["completeness", reportId] });
    queryClient.invalidateQueries({ queryKey: ["exposure", reportId] });
    queryClient.invalidateQueries({ queryKey: ["cashflow", reportId] });
    queryClient.invalidateQueries({ queryKey: ["guarantee-validation", reportId] });
  };

  const classifyMutation = useMutation({
    mutationFn: async ({ txId, category, category_primary, subcategory }: {
      txId: number;
      category?: string | null;
      category_primary?: string | null;
      subcategory?: string | null;
    }) => {
      const body: Record<string, unknown> = {};
      if (category !== undefined) body.category = category;
      if (category_primary !== undefined) body.category_primary = category_primary;
      if (subcategory !== undefined) body.subcategory = subcategory;
      return api.patch(`/projects/${projectId}/monthly-reports/${reportId}/transactions/${txId}`, body);
    },
    onSuccess: invalidateBudgetDependentQueries,
  });

  const { data: bankSummary } = useQuery({
    queryKey: ["bank-summary", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/bank-summary`)).data,
    enabled: transactions.length > 0,
  });

  const deleteTxMutation = useMutation({
    mutationFn: (txId: number) =>
      api.delete(`/projects/${projectId}/monthly-reports/${reportId}/transactions/${txId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions", reportId] });
      queryClient.invalidateQueries({ queryKey: ["completeness", reportId] });
      queryClient.invalidateQueries({ queryKey: ["bank-summary", reportId] });
    },
  });

  const autoClassifyMutation = useMutation({
    mutationFn: async () => {
      return (await api.post(`/projects/${projectId}/monthly-reports/${reportId}/transactions/auto-classify`)).data;
    },
    onSuccess: invalidateBudgetDependentQueries,
  });

  const bulkApproveMutation = useMutation({
    mutationFn: async (pairs: { txId: number; category: string }[]) => {
      await Promise.all(
        pairs.map(({ txId, category }) =>
          api.patch(`/projects/${projectId}/monthly-reports/${reportId}/transactions/${txId}`, { category })
        )
      );
      return pairs.length;
    },
    onSuccess: () => {
      setSelectedTxIds(new Set());
      invalidateBudgetDependentQueries();
    },
  });

  // Every row can be selected so the user can group classified + unclassified
  // rows together. The bulk-approve action only applies an AI suggestion
  // where one exists; rows without a suggestion are skipped silently.
  const selectableTxIds = transactions.map((t) => t.id);
  const allSelectableSelected = selectableTxIds.length > 0 && selectableTxIds.every((id) => selectedTxIds.has(id));
  const toggleRowSelection = (txId: number) => {
    setSelectedTxIds((prev) => {
      const next = new Set(prev);
      if (next.has(txId)) next.delete(txId);
      else next.add(txId);
      return next;
    });
  };
  const toggleSelectAll = () => {
    setSelectedTxIds(allSelectableSelected ? new Set() : new Set(selectableTxIds));
  };
  const handleBulkApprove = () => {
    const pairs = transactions
      .filter((t) => selectedTxIds.has(t.id) && !t.category && t.ai_suggested_category)
      .map((t) => ({ txId: t.id, category: t.ai_suggested_category as string }));
    if (pairs.length > 0) bulkApproveMutation.mutate(pairs);
  };

  const unclassifiedCount = transactions.filter((t) => !t.category).length;
  const totalCredits = transactions.filter((t) => t.transaction_type === "credit").reduce((s, t) => s + Number(t.amount), 0);
  const totalDebits = transactions.filter((t) => t.transaction_type === "debit").reduce((s, t) => s + Number(t.amount), 0);

  // Show upload zone when no data exists and nothing was just uploaded
  const showUploadZone = !hasExistingData && !uploadResult;
  // Show review step after upload, before user approves
  const showReviewStep = uploadResult && !approved;
  // Show full transaction view when user approved or data already existed
  const showTransactionView = hasExistingData || approved;

  return (
    <div>
      {/* ─── Upload Zone ─── */}
      {showUploadZone && (
        <div
          className="bg-white rounded-2xl border-2 border-dashed border-gray-200 hover:border-primary/40 p-12 text-center mb-6 cursor-pointer transition"
          onClick={triggerFileSelect}
        >
          {uploading ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-gray-600 font-medium">מפרסר ומסווג את התדפיס...</p>
              <p className="text-gray-400 text-sm">זה עשוי לקחת כ-30 שניות</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <Upload size={48} className="text-gray-400" />
              <p className="text-gray-700 font-medium text-lg">העלה תדפיס בנק</p>
              <p className="text-gray-400">PDF או Excel - המערכת תפרסר ותסווג אוטומטית</p>
            </div>
          )}
        </div>
      )}

      {/* ─── Review Step (after upload, before approve) ─── */}
      {showReviewStep && (
        <div className="space-y-4 mb-6">
          {/* Summary card */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center">
                <FileText size={20} className="text-green-600" />
              </div>
              <div>
                <h3 className="font-bold text-gray-900">תדפיס נסרק בהצלחה</h3>
                <p className="text-sm text-gray-500">בדוק את הנתונים לפני אישור</p>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="bg-gray-50 rounded-xl p-3 text-center">
                <p className="text-2xl font-bold text-gray-900">{uploadResult.transactions_count}</p>
                <p className="text-xs text-gray-500">תנועות זוהו</p>
              </div>
              <div className="bg-blue-50 rounded-xl p-3 text-center">
                <p className="text-2xl font-bold text-blue-700">{uploadResult.bank_name || "—"}</p>
                <p className="text-xs text-gray-500">בנק</p>
              </div>
              <div className="bg-purple-50 rounded-xl p-3 text-center">
                <p className="text-2xl font-bold text-purple-700">{uploadResult.auto_classified}</p>
                <p className="text-xs text-gray-500">סווגו אוטומטית</p>
              </div>
            </div>

            {/* Warnings */}
            {uploadResult.warnings.length > 0 && (
              <div className="bg-amber-50 rounded-xl border border-amber-200 p-3 mb-4">
                <div className="flex items-center gap-2 mb-1">
                  <AlertTriangle size={14} className="text-amber-600" />
                  <p className="text-xs font-medium text-amber-800">הערות</p>
                </div>
                {uploadResult.warnings.map((w, i) => (
                  <p key={i} className="text-xs text-amber-700">{w}</p>
                ))}
              </div>
            )}

            {/* Preview table - show first 5 transactions */}
            {transactions.length > 0 && (
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <Eye size={14} className="text-gray-400" />
                  <p className="text-xs font-medium text-gray-500">תצוגה מקדימה (5 תנועות ראשונות)</p>
                </div>
                <div className="overflow-x-auto rounded-lg border border-gray-100">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-gray-50 text-gray-500">
                        <th className="text-right px-3 py-2 font-medium">תאריך</th>
                        <th className="text-right px-3 py-2 font-medium">תיאור</th>
                        <th className="text-left px-3 py-2 font-medium">סכום</th>
                        <th className="text-left px-3 py-2 font-medium">יתרה</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {transactions.slice(0, 5).map((tx) => (
                        <tr key={tx.id}>
                          <td className="px-3 py-2 text-gray-600">{formatDate(tx.transaction_date)}</td>
                          <td className="px-3 py-2 text-gray-900 max-w-[200px] truncate">{tx.description}</td>
                          <td className={`px-3 py-2 font-medium text-left ${
                            tx.transaction_type === "credit" ? "text-green-600" : "text-red-600"
                          }`}>
                            {tx.transaction_type === "credit" ? "+" : "-"}{formatCurrency(Number(tx.amount))}
                          </td>
                          <td className="px-3 py-2 text-gray-500 text-left">
                            {tx.balance ? formatCurrency(Number(tx.balance)) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {transactions.length > 5 && (
                  <p className="text-xs text-gray-400 mt-1 text-center">
                    ועוד {transactions.length - 5} תנועות נוספות...
                  </p>
                )}
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleApprove}
                className="flex-1 flex items-center justify-center gap-2 py-3 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 transition"
              >
                <CheckCircle size={18} />
                אשר והמשך
              </button>
              <button
                onClick={handleReplace}
                className="flex items-center justify-center gap-2 px-5 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition"
              >
                <RefreshCw size={16} />
                סרוק קובץ אחר
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Full Transaction View (after approve or existing data) ─── */}
      {showTransactionView && (
        <>
          {/* Balance + Summary stats */}
          {bankSummary && (bankSummary.opening_balance != null || bankSummary.closing_balance != null) && (
            <div className="bg-white rounded-2xl border border-gray-200 p-4 mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Wallet size={18} className="text-gray-400" />
                <span className="text-sm text-gray-500">
                  {bankSummary.bank_name || "חשבון"} {bankSummary.account_number ? `(${bankSummary.account_number})` : ""}
                </span>
              </div>
              <div className="flex gap-6">
                {bankSummary.opening_balance != null && (
                  <div className="text-left">
                    <p className="text-xs text-gray-400">יתרת פתיחה</p>
                    <p className="text-sm font-bold text-gray-700">{formatCurrency(bankSummary.opening_balance)}</p>
                  </div>
                )}
                {bankSummary.closing_balance != null && (
                  <div className="text-left">
                    <p className="text-xs text-gray-400">יתרת סגירה</p>
                    <p className="text-sm font-bold text-gray-900">{formatCurrency(bankSummary.closing_balance)}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="grid grid-cols-3 gap-4 mb-4">
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

          {/* Replace file + Auto-classify buttons */}
          <div className="mb-4 flex justify-between">
            <button
              onClick={handleReplace}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-200 transition"
            >
              <RefreshCw size={14} />
              העלה תדפיס אחר
            </button>
            <div className="flex items-center gap-2">
              {selectedTxIds.size > 0 && (
                <button
                  onClick={handleBulkApprove}
                  disabled={bulkApproveMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-xl text-sm font-medium hover:bg-green-700 transition disabled:opacity-50"
                >
                  <CheckCircle size={16} />
                  {bulkApproveMutation.isPending ? "מאשר..." : `אשר סיווג AI למסומנים (${selectedTxIds.size})`}
                </button>
              )}
              {unclassifiedCount > 0 && (
                <button
                  onClick={() => autoClassifyMutation.mutate()}
                  disabled={autoClassifyMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-xl text-sm font-medium hover:bg-purple-700 transition disabled:opacity-50"
                >
                  <Sparkles size={16} />
                  {autoClassifyMutation.isPending ? "מסווג..." : `סווג אוטומטי (${unclassifiedCount} תנועות)`}
                </button>
              )}
            </div>
          </div>

          {/* Transaction table */}
          <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-xs text-gray-500 bg-gray-50 border-b">
                    <th className="w-10 px-2 py-3">
                      {selectableTxIds.length > 0 && (
                        <input
                          type="checkbox"
                          checked={allSelectableSelected}
                          onChange={toggleSelectAll}
                          className="w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500 cursor-pointer"
                          title="בחר הכל"
                        />
                      )}
                    </th>
                    <th className="text-right px-4 py-3 font-medium">תאריך</th>
                    <th className="text-right px-4 py-3 font-medium">תיאור</th>
                    <th className="text-left px-4 py-3 font-medium">סכום</th>
                    <th className="text-left px-4 py-3 font-medium">יתרה</th>
                    <th className="text-right px-4 py-3 font-medium w-52">סיווג</th>
                    <th className="w-10"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {transactions.map((tx) => {
                    const isSelectable = true;
                    return (
                    <tr key={tx.id} className={`hover:bg-gray-50/50 transition ${!tx.category ? "bg-amber-50/30" : ""}`}>
                      <td className="px-2 py-3 text-center">
                        {isSelectable && (
                          <input
                            type="checkbox"
                            checked={selectedTxIds.has(tx.id)}
                            onChange={() => toggleRowSelection(tx.id)}
                            className="w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500 cursor-pointer"
                          />
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">{formatDate(tx.transaction_date)}</td>
                      <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate">
                        {tx.description}
                        {tx.ai_suggested_category && !tx.is_manually_classified && tx.category && (
                          <span className="inline-flex items-center gap-1 mr-2 px-1.5 py-0.5 bg-purple-50 text-purple-600 rounded text-[10px]">
                            <Sparkles size={10} /> AI
                          </span>
                        )}
                      </td>
                      <td className={`px-4 py-3 text-sm font-medium text-left whitespace-nowrap ${
                        tx.transaction_type === "credit" ? "text-green-600" : "text-red-600"
                      }`}>
                        {tx.transaction_type === "credit" ? "+" : "-"}{formatCurrency(Number(tx.amount))}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 text-left whitespace-nowrap">
                        {tx.balance ? formatCurrency(Number(tx.balance)) : "—"}
                      </td>
                      <td className="px-4 py-3">
                        {(() => {
                          const primaryKey = tx.category_primary || (tx.category ? taxonomy?.legacy_to_primary?.[tx.category] : null);
                          const isExpense = primaryKey ? EXPENSE_PRIMARIES.has(primaryKey) : tx.transaction_type === "debit";
                          const colorClass = primaryKey
                            ? isExpense
                              ? "border-red-200 bg-red-50 text-red-800"
                              : "border-green-200 bg-green-50 text-green-800"
                            : "border-amber-200 bg-amber-50 text-amber-800";
                          // Filter primaries by transaction direction.
                          const expenseGroupKeys = ["tenant_expenses", "land_and_taxes", "indirect_costs", "direct_construction", "interest_fees_guarantees", "withdrawals"];
                          const incomeGroupKeys = ["receipts", "deposits"];
                          const allowedPrimaries = (taxonomy?.primaries || []).filter((p) =>
                            tx.transaction_type === "debit"
                              ? expenseGroupKeys.includes(p.key)
                              : incomeGroupKeys.includes(p.key)
                          );
                          const otherPrimaries = (taxonomy?.primaries || []).filter((p) =>
                            !allowedPrimaries.some((a) => a.key === p.key)
                          );
                          const secondaries = primaryKey ? (taxonomy?.secondaries?.[primaryKey] || []) : [];
                          const isBudgetLine = primaryKey ? BUDGET_LINE_PRIMARIES.has(primaryKey) : false;
                          return (
                            <div className="flex gap-1.5">
                              <select
                                value={primaryKey || ""}
                                onChange={(e) => {
                                  const next = e.target.value || null;
                                  classifyMutation.mutate({
                                    txId: tx.id,
                                    category_primary: next,
                                    subcategory: null,
                                    // also set the legacy flat category for budget-line primaries
                                    category: next && BUDGET_LINE_PRIMARIES.has(next) ? next : tx.category,
                                  });
                                }}
                                className={`flex-1 px-2 py-1.5 rounded-lg border text-xs ${colorClass} focus:outline-none focus:ring-2 focus:ring-primary/20`}
                              >
                                <option value="">
                                  {tx.ai_suggested_category && !primaryKey
                                    ? `💡 ${taxonomy?.legacy_to_primary?.[tx.ai_suggested_category] ? taxonomy.primaries.find(p => p.key === taxonomy.legacy_to_primary[tx.ai_suggested_category!])?.label : tx.ai_suggested_category}`
                                    : "— ראשי —"}
                                </option>
                                {allowedPrimaries.map((p) => (
                                  <option key={p.key} value={p.key}>{p.label}</option>
                                ))}
                                {otherPrimaries.length > 0 && (
                                  <optgroup label="כיוון נגדי">
                                    {otherPrimaries.map((p) => (
                                      <option key={p.key} value={p.key}>{p.label}</option>
                                    ))}
                                  </optgroup>
                                )}
                              </select>
                              {primaryKey && !isBudgetLine && (
                                <select
                                  value={tx.subcategory || ""}
                                  onChange={(e) => classifyMutation.mutate({ txId: tx.id, subcategory: e.target.value || null })}
                                  className={`flex-1 px-2 py-1.5 rounded-lg border text-xs ${colorClass} focus:outline-none focus:ring-2 focus:ring-primary/20`}
                                >
                                  <option value="">— משני —</option>
                                  {secondaries.map((s) => (
                                    <option key={s.key} value={s.key}>{s.label}</option>
                                  ))}
                                </select>
                              )}
                              {primaryKey && isBudgetLine && (() => {
                                const lines = budgetLinesByCategory[primaryKey] || [];
                                if (lines.length === 0) {
                                  return (
                                    <span className="flex-1 px-2 py-1.5 text-xs text-gray-400 italic">
                                      אין סעיפי תקציב בקטגוריה זו
                                    </span>
                                  );
                                }
                                return (
                                  <select
                                    value={tx.subcategory || ""}
                                    onChange={(e) => classifyMutation.mutate({ txId: tx.id, subcategory: e.target.value || null })}
                                    className={`flex-1 px-2 py-1.5 rounded-lg border text-xs ${colorClass} focus:outline-none focus:ring-2 focus:ring-primary/20`}
                                  >
                                    <option value="">— סעיף תקציב —</option>
                                    {lines.map((line) => (
                                      <option key={line.id} value={`budget_line_${line.id}`}>
                                        {line.description}
                                      </option>
                                    ))}
                                  </select>
                                );
                              })()}
                            </div>
                          );
                        })()}
                      </td>
                      <td className="px-2 py-3">
                        <button
                          onClick={() => deleteTxMutation.mutate(tx.id)}
                          className="text-gray-300 hover:text-red-500 transition p-1"
                          title="מחק תנועה"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Navigation */}
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
        </>
      )}
    </div>
  );
}
