"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  FolderKanban, Plus, TrendingUp, Building2, Banknote,
  ShieldCheck, HardHat, BarChart3, ChevronLeft,
} from "lucide-react";
import api from "@/lib/api";
import { formatPercent } from "@/lib/formatters";

interface ProjectKPI {
  id: number;
  name: string;
  city: string | null;
  phase: string;
  current_report: number;
  units: number;
  sold: number;
  sold_percent: number;
  recognized: number;
  recognized_percent: number;
  budget_percent: number;
  construction_percent: number;
}

interface DashboardData {
  projects: ProjectKPI[];
  totals: {
    active_projects: number;
    total_units: number;
    total_sold: number;
    sold_percent: number;
    total_recognized: number;
    recognized_percent: number;
    avg_budget_percent: number;
    avg_construction_percent: number;
  };
}

export default function DashboardPage() {
  const { data, isLoading } = useQuery<DashboardData>({
    queryKey: ["dashboard-kpis"],
    queryFn: async () => (await api.get("/dashboard/kpis")).data,
  });

  const totals = data?.totals;
  const projects = data?.projects || [];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">דשבורד</h1>
          <p className="text-gray-500 mt-1">סקירה כללית של כל הפרויקטים</p>
        </div>
        <Link
          href="/projects/new"
          className="flex items-center gap-2 px-5 py-2.5 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition"
        >
          <Plus size={18} />
          פרויקט חדש
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <KPICard
          icon={<FolderKanban size={22} />}
          label="פרויקטים פעילים"
          value={String(totals?.active_projects || 0)}
          color="blue"
        />
        <KPICard
          icon={<BarChart3 size={22} />}
          label="ניצול תקציב ממוצע"
          value={formatPercent(totals?.avg_budget_percent || 0)}
          color="purple"
        />
        <KPICard
          icon={<HardHat size={22} />}
          label="ביצוע פיזי ממוצע"
          value={formatPercent(totals?.avg_construction_percent || 0)}
          color="amber"
        />
        <KPICard
          icon={<Banknote size={22} />}
          label="חוזים חתומים"
          value={`${totals?.total_sold || 0} / ${totals?.total_units || 0}`}
          sub={formatPercent(totals?.sold_percent || 0)}
          color="green"
        />
        <KPICard
          icon={<ShieldCheck size={22} />}
          label="מכירות מוכרות (>15%)"
          value={`${totals?.total_recognized || 0}`}
          sub={formatPercent(totals?.recognized_percent || 0)}
          color="teal"
        />
      </div>

      {/* Projects Table */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-bold text-gray-900">פרויקטים</h2>
          <span className="text-sm text-gray-500">{projects.length} פרויקטים</span>
        </div>

        {isLoading ? (
          <div className="p-12 text-center">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          </div>
        ) : projects.length === 0 ? (
          <div className="p-12 text-center">
            <FolderKanban size={48} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500 mb-4">אין פרויקטים עדיין</p>
            <Link
              href="/projects/new"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition"
            >
              <Plus size={18} />
              צור פרויקט ראשון
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-500 bg-gray-50 border-b">
                  <th className="text-right px-6 py-3 font-medium">פרויקט</th>
                  <th className="text-center px-4 py-3 font-medium">דוח</th>
                  <th className="text-center px-4 py-3 font-medium">יח&quot;ד</th>
                  <th className="text-center px-4 py-3 font-medium">נמכרו</th>
                  <th className="text-center px-4 py-3 font-medium">מוכרות</th>
                  <th className="text-center px-4 py-3 font-medium">תקציב</th>
                  <th className="text-center px-4 py-3 font-medium">בנייה</th>
                  <th className="text-center px-4 py-3 font-medium">סטטוס</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {projects.map((project) => (
                  <tr
                    key={project.id}
                    className="hover:bg-gray-50/50 transition cursor-pointer"
                    onClick={() => (window.location.href = `/projects/${project.id}`)}
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0">
                          <Building2 size={20} />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{project.name}</p>
                          <p className="text-xs text-gray-500">{project.city || "—"}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-center">
                      <span className="font-bold text-gray-900">#{project.current_report}</span>
                    </td>
                    <td className="px-4 py-4 text-center text-gray-700">{project.units}</td>
                    <td className="px-4 py-4 text-center">
                      <span className="font-medium">{project.sold}</span>
                      <span className="text-xs text-gray-400 mr-1">({formatPercent(project.sold_percent)})</span>
                    </td>
                    <td className="px-4 py-4 text-center">
                      <span className="font-medium">{project.recognized}</span>
                      <span className="text-xs text-gray-400 mr-1">({formatPercent(project.recognized_percent)})</span>
                    </td>
                    <td className="px-4 py-4 text-center">
                      <ProgressPill value={project.budget_percent} />
                    </td>
                    <td className="px-4 py-4 text-center">
                      <ProgressPill value={project.construction_percent} color="amber" />
                    </td>
                    <td className="px-4 py-4 text-center">
                      <PhaseTag phase={project.phase} />
                    </td>
                    <td className="px-4 py-4">
                      <Link href={`/projects/${project.id}`} className="text-gray-400 hover:text-primary transition">
                        <ChevronLeft size={18} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function KPICard({
  icon, label, value, sub, color,
}: {
  icon: React.ReactNode; label: string; value: string; sub?: string;
  color: "blue" | "green" | "amber" | "purple" | "teal";
}) {
  const colors = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-green-50 text-green-600",
    amber: "bg-amber-50 text-amber-600",
    purple: "bg-purple-50 text-purple-600",
    teal: "bg-teal-50 text-teal-600",
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-5">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${colors[color]}`}>
        {icon}
      </div>
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function ProgressPill({ value, color = "blue" }: { value: number; color?: "blue" | "amber" }) {
  const bg = color === "amber" ? "bg-amber-100" : "bg-blue-100";
  const fill = color === "amber" ? "bg-amber-500" : "bg-blue-500";
  const text = color === "amber" ? "text-amber-700" : "text-blue-700";

  return (
    <div className="flex items-center gap-2">
      <div className={`w-16 h-2 rounded-full ${bg} overflow-hidden`}>
        <div className={`h-full rounded-full ${fill}`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
      <span className={`text-xs font-medium ${text}`}>{formatPercent(value)}</span>
    </div>
  );
}

function PhaseTag({ phase }: { phase: string }) {
  const config: Record<string, { label: string; className: string }> = {
    setup: { label: "הגדרה", className: "bg-amber-50 text-amber-700" },
    active: { label: "פעיל", className: "bg-green-50 text-green-700" },
    completed: { label: "הושלם", className: "bg-gray-100 text-gray-600" },
  };
  const c = config[phase] || config.setup;
  return (
    <span className={`px-3 py-1 rounded-lg text-xs font-medium ${c.className}`}>
      {c.label}
    </span>
  );
}
