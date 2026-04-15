"use client";

import { useParams, usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  ArrowRight, Upload, ShoppingCart, HardHat,
  TrendingUp, Shield, ClipboardCheck, FileDown, CheckCircle2, CreditCard,
} from "lucide-react";
import api from "@/lib/api";

interface DataCompleteness {
  bank_statement_uploaded: boolean;
  all_transactions_classified: boolean;
  construction_progress_entered: boolean;
  index_updated: boolean;
  ready_to_generate: boolean;
  missing_items: string[];
}

const STEPS = [
  { key: "bank-statement", label: "תדפיס בנק", icon: Upload, completenessKey: "bank_statement_uploaded" },
  { key: "sales", label: "מכירות", icon: ShoppingCart, completenessKey: null },
  { key: "construction", label: "התקדמות בנייה", icon: HardHat, completenessKey: "construction_progress_entered" },
  { key: "index", label: "מדד", icon: TrendingUp, completenessKey: "index_updated" },
  { key: "guarantees", label: "ערבויות", icon: Shield, completenessKey: null },
  { key: "checks", label: "אישורי שיקים", icon: CreditCard, completenessKey: null },
  { key: "review", label: "סקירה", icon: ClipboardCheck, completenessKey: null },
  { key: "generate", label: "הפקת דוח", icon: FileDown, completenessKey: "ready_to_generate" },
];

export default function MonthlyReportLayout({ children }: { children: React.ReactNode }) {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const pathname = usePathname();
  const router = useRouter();

  const { data: report } = useQuery({
    queryKey: ["report", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}`)).data,
  });

  const { data: completeness } = useQuery<DataCompleteness>({
    queryKey: ["completeness", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/completeness`)).data,
    refetchInterval: 10_000,
  });

  const currentStep = STEPS.findIndex((s) => pathname.includes(s.key));
  const basePath = `/projects/${projectId}/monthly/${reportId}`;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push(`/projects/${projectId}/monthly`)} className="text-gray-400 hover:text-gray-600 transition">
            <ArrowRight size={20} />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              דוח מעקב #{report?.report_number || "..."}
            </h1>
            <p className="text-sm text-gray-500">
              {report?.report_month ? new Date(report.report_month).toLocaleDateString("he-IL", { month: "long", year: "numeric" }) : ""}
            </p>
          </div>
        </div>
      </div>

      {/* Stepper */}
      <div className="bg-white rounded-2xl border border-gray-200 p-4 mb-6">
        <div className="flex items-center justify-between">
          {STEPS.map((step, idx) => {
            const isActive = idx === currentStep;
            const isPast = idx < currentStep;
            const isComplete = step.completenessKey && completeness
              ? (completeness as unknown as Record<string, boolean>)[step.completenessKey]
              : false;
            const Icon = step.icon;

            return (
              <Link
                key={step.key}
                href={`${basePath}/${step.key}`}
                className="flex flex-col items-center gap-1.5 flex-1 group"
              >
                {/* Circle */}
                <div className={`w-10 h-10 rounded-full flex items-center justify-center transition ${
                  isActive
                    ? "bg-primary text-white shadow-md shadow-primary/30"
                    : isComplete
                    ? "bg-green-100 text-green-600"
                    : isPast
                    ? "bg-primary/10 text-primary"
                    : "bg-gray-100 text-gray-400 group-hover:bg-gray-200"
                }`}>
                  {isComplete && !isActive ? <CheckCircle2 size={20} /> : <Icon size={18} />}
                </div>

                {/* Label */}
                <span className={`text-xs font-medium ${
                  isActive ? "text-primary" : "text-gray-500"
                }`}>
                  {step.label}
                </span>

                {/* Connector line */}
                {idx < STEPS.length - 1 && (
                  <div className="absolute" style={{ display: "none" }} />
                )}
              </Link>
            );
          })}
        </div>
      </div>

      {/* Content */}
      {children}
    </div>
  );
}
