"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight, Receipt, Building2, Landmark, HardHat, Flag,
  CheckCircle2, Circle, FileSpreadsheet, ChevronLeft, Upload, X,
  CheckCircle, AlertTriangle, FileUp,
} from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { formatCurrencyShort, formatCurrency, formatNumber } from "@/lib/formatters";

interface SetupStatus {
  budget: boolean;
  apartments: boolean;
  financing: boolean;
  contractor: boolean;
  milestones: boolean;
  budget_items_count: number;
  apartments_count: number;
  total_budget: number;
}

interface ProjectDetail {
  id: number;
  project_name: string;
  address: string | null;
  city: string | null;
  phase: string;
  current_report_number: number;
  developer_name: string | null;
  bank: string | null;
  total_units: number | null;
  base_index: number | null;
}

const SETUP_SECTIONS = [
  {
    key: "budget",
    label: "תקציב (סעיף 8)",
    description: "הגדרת תקציב הפרויקט לפי סעיפים",
    icon: Receipt,
    href: "setup/budget",
    color: "blue",
  },
  {
    key: "apartments",
    label: "מלאי דירות",
    description: "יחידות דיור - יזם ובעלים",
    icon: Building2,
    href: "setup/apartments",
    color: "green",
  },
  {
    key: "financing",
    label: "תנאי מימון",
    description: "הסכם ליווי, מסגרות אשראי, הון עצמי",
    icon: Landmark,
    href: "setup/financing",
    color: "purple",
  },
  {
    key: "contractor",
    label: "הסכם קבלן",
    description: "תמורה, מדד בסיס, ערבויות, עיכבון",
    icon: HardHat,
    href: "setup/contractor",
    color: "orange",
  },
  {
    key: "milestones",
    label: "אבני דרך",
    description: "לוחות זמנים - היתר, יסודות, שלד, טופס 4",
    icon: Flag,
    href: "setup/milestones",
    color: "teal",
  },
];

interface BulkPreview {
  summary: {
    developer_residential_count: number;
    developer_commercial_count: number;
    resident_residential_count: number;
    resident_commercial_count: number;
    total_apartments: number;
    budget_line_count: number;
    budget_total: number;
    budget_categories_count: number;
    guarantee_count: number;
    guarantee_total: number;
    has_financing: boolean;
  };
  warnings: string[];
  tabs_found: string[];
  [key: string]: unknown;
}

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const qc = useQueryClient();
  const [bulkPreview, setBulkPreview] = useState<BulkPreview | null>(null);
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkError, setBulkError] = useState("");

  const { data: project } = useQuery<ProjectDetail>({
    queryKey: ["project", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}`)).data,
  });

  const { data: status } = useQuery<SetupStatus>({
    queryKey: ["setup-status", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/setup/status`)).data,
  });

  const handleBulkUpload = async (file: File) => {
    setBulkUploading(true);
    setBulkError("");
    setBulkPreview(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post(
        `/projects/${projectId}/setup/bulk-upload/preview`,
        formData,
      );
      setBulkPreview(data);
    } catch (err: any) {
      setBulkError(err?.response?.data?.detail || "שגיאה בפרסור הקובץ");
    } finally {
      setBulkUploading(false);
    }
  };

  const confirmMutation = useMutation({
    mutationFn: async () => {
      if (!bulkPreview) return;
      return api.post(`/projects/${projectId}/setup/bulk-upload/confirm`, bulkPreview);
    },
    onSuccess: () => {
      setBulkPreview(null);
      qc.invalidateQueries({ queryKey: ["setup-status", projectId] });
      qc.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });

  if (!project) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const completedCount = status
    ? [status.budget, status.apartments, status.financing, status.contractor, status.milestones].filter(Boolean).length
    : 0;

  return (
    <div>
      {/* Back + Header */}
      <Link href="/dashboard" className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4 transition">
        <ArrowRight size={18} />
        חזרה לדשבורד
      </Link>

      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{project.project_name}</h1>
          <p className="text-gray-500 mt-1">
            {[project.address, project.city].filter(Boolean).join(", ") || "—"}
            {project.developer_name && ` | ${project.developer_name}`}
          </p>
        </div>

        {/* Quick Stats */}
        <div className="flex gap-4">
          {project.total_units && (
            <div className="text-center px-4 py-2 bg-white rounded-xl border border-gray-200">
              <p className="text-2xl font-bold text-gray-900">{project.total_units}</p>
              <p className="text-xs text-gray-500">יח&quot;ד</p>
            </div>
          )}
          <div className="text-center px-4 py-2 bg-white rounded-xl border border-gray-200">
            <p className="text-2xl font-bold text-gray-900">#{project.current_report_number}</p>
            <p className="text-xs text-gray-500">דוח נוכחי</p>
          </div>
        </div>
      </div>

      {/* Bulk Upload */}
      {!bulkPreview && (
        <div className="mb-6">
          <div
            className="bg-white rounded-2xl border-2 border-dashed border-primary/30 hover:border-primary/60 p-6 text-center cursor-pointer transition"
            onClick={() => {
              const input = document.createElement("input");
              input.type = "file";
              input.accept = ".xlsx,.xls";
              input.onchange = (e) => {
                const f = (e.target as HTMLInputElement).files?.[0];
                if (f) handleBulkUpload(f);
              };
              input.click();
            }}
          >
            {bulkUploading ? (
              <div className="flex flex-col items-center gap-2">
                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                <p className="text-gray-600 font-medium">מנתח את הקובץ...</p>
              </div>
            ) : (
              <div className="flex items-center justify-center gap-3">
                <FileUp size={24} className="text-primary/60" />
                <div className="text-right">
                  <p className="font-medium text-gray-900">העלאת קובץ הזנת נתונים מאוחד</p>
                  <p className="text-sm text-gray-400">Excel עם 8 טאבים — מלאי, תקציב, ערבויות, חשבון ליווי</p>
                </div>
              </div>
            )}
          </div>
          {bulkError && (
            <div className="mt-2 bg-red-50 border border-red-200 rounded-xl p-3 text-red-700 text-sm">{bulkError}</div>
          )}
        </div>
      )}

      {/* Bulk Upload Preview */}
      {bulkPreview && (
        <div className="mb-6 bg-white rounded-2xl border-2 border-primary/30 overflow-hidden">
          <div className="p-6 border-b border-gray-100">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <CheckCircle size={22} className="text-green-500" />
                סיכום הקובץ שהועלה
              </h2>
              <button onClick={() => setBulkPreview(null)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              טאבים שזוהו: {bulkPreview.tabs_found.join(", ")}
            </p>
          </div>

          <div className="p-6">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
              <SummaryCard label="דירות מגורים יזם" value={bulkPreview.summary.developer_residential_count} />
              <SummaryCard label="מסחרי יזם" value={bulkPreview.summary.developer_commercial_count} />
              <SummaryCard label="דירות מגורים בעלים" value={bulkPreview.summary.resident_residential_count} />
              <SummaryCard label="מסחרי בעלים" value={bulkPreview.summary.resident_commercial_count} />
              <SummaryCard label='סה"כ נכסים' value={bulkPreview.summary.total_apartments} highlight />
              <SummaryCard label="סעיפי תקציב" value={bulkPreview.summary.budget_line_count} sub={`${bulkPreview.summary.budget_categories_count} קטגוריות`} />
              <SummaryCard label='סה"כ תקציב' value={formatCurrencyShort(bulkPreview.summary.budget_total)} />
              <SummaryCard label="ערבויות" value={bulkPreview.summary.guarantee_count} sub={formatCurrencyShort(bulkPreview.summary.guarantee_total)} />
              <SummaryCard label="חשבון ליווי" value={bulkPreview.summary.has_financing ? "נמצא" : "לא נמצא"} />
            </div>

            {bulkPreview.warnings.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
                <div className="flex items-center gap-2 mb-1">
                  <AlertTriangle size={16} className="text-amber-600" />
                  <span className="text-sm font-bold text-amber-800">אזהרות:</span>
                </div>
                {bulkPreview.warnings.map((w, i) => (
                  <p key={i} className="text-sm text-amber-700">- {w}</p>
                ))}
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => confirmMutation.mutate()}
                disabled={confirmMutation.isPending}
                className="flex-1 py-3 bg-primary text-white rounded-xl font-bold hover:bg-primary-dark transition disabled:opacity-50"
              >
                {confirmMutation.isPending ? "שומר..." : "אשר והעלה נתונים"}
              </button>
              <button
                onClick={() => setBulkPreview(null)}
                className="px-6 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition"
              >
                ביטול
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Setup Progress */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">הגדרת פרויקט</h2>
          <span className="text-sm text-gray-500">{completedCount}/5 הושלמו</span>
        </div>

        {/* Progress bar */}
        <div className="w-full h-2 bg-gray-100 rounded-full mb-6 overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500"
            style={{ width: `${(completedCount / 5) * 100}%` }}
          />
        </div>

        {/* Setup Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {SETUP_SECTIONS.map((section) => {
            const isComplete = status?.[section.key as keyof SetupStatus] === true;
            const Icon = section.icon;

            return (
              <Link
                key={section.key}
                href={`/projects/${projectId}/${section.href}`}
                className={`group relative bg-white rounded-2xl border-2 p-6 transition-all hover:shadow-md ${
                  isComplete ? "border-green-200" : "border-gray-100 hover:border-primary/30"
                }`}
              >
                {/* Status indicator */}
                <div className="absolute top-4 left-4">
                  {isComplete ? (
                    <CheckCircle2 size={22} className="text-green-500" />
                  ) : (
                    <Circle size={22} className="text-gray-300" />
                  )}
                </div>

                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
                    isComplete ? "bg-green-50 text-green-600" : "bg-gray-50 text-gray-400 group-hover:bg-primary/10 group-hover:text-primary"
                  } transition`}>
                    <Icon size={24} />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-bold text-gray-900">{section.label}</h3>
                    <p className="text-sm text-gray-500 mt-0.5">{section.description}</p>

                    {/* Stats */}
                    {section.key === "budget" && status && status.budget_items_count > 0 && (
                      <p className="text-xs text-primary mt-2 font-medium">
                        {status.budget_items_count} סעיפים | {formatCurrencyShort(status.total_budget)}
                      </p>
                    )}
                    {section.key === "apartments" && status && status.apartments_count > 0 && (
                      <p className="text-xs text-primary mt-2 font-medium">
                        {status.apartments_count} יחידות
                      </p>
                    )}
                  </div>
                </div>

                <ChevronLeft size={18} className="absolute bottom-4 left-4 text-gray-300 group-hover:text-primary transition" />
              </Link>
            );
          })}
        </div>
      </div>

      {/* Monthly Reports Section */}
      <div className="mt-8">
        <Link
          href={`/projects/${projectId}/monthly`}
          className="block bg-white rounded-2xl border-2 border-primary/20 hover:border-primary/50 p-8 text-center transition group"
        >
          <FileSpreadsheet size={48} className="mx-auto text-primary/60 group-hover:text-primary mb-3 transition" />
          <h3 className="font-bold text-gray-900 mb-1 text-lg">דוחות מעקב חודשיים</h3>
          <p className="text-gray-500 text-sm">
            {project.current_report_number > 0
              ? `${project.current_report_number} דוחות | לחץ לצפייה ויצירת דוח חדש`
              : "לחץ ליצירת דוח מעקב ראשון"
            }
          </p>
        </Link>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, sub, highlight }: { label: string; value: string | number; sub?: string; highlight?: boolean }) {
  return (
    <div className={`rounded-xl p-4 text-center ${highlight ? "bg-primary/10 border border-primary/20" : "bg-gray-50"}`}>
      <p className={`text-xl font-bold ${highlight ? "text-primary" : "text-gray-900"}`}>{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}
