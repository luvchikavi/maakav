"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FolderKanban, Plus, TrendingUp, Building2, Banknote, ShieldCheck } from "lucide-react";
import api from "@/lib/api";
import { formatCurrencyShort, formatPercent } from "@/lib/formatters";

interface Project {
  id: number;
  project_name: string;
  city: string | null;
  phase: string;
  current_report_number: number;
  total_units: number | null;
}

export default function DashboardPage() {
  const { data: projects = [], isLoading } = useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: async () => (await api.get("/projects")).data,
  });

  const activeProjects = projects.filter((p) => p.phase === "active");
  const setupProjects = projects.filter((p) => p.phase === "setup");

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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        <KPICard
          icon={<FolderKanban size={22} />}
          label="פרויקטים פעילים"
          value={String(activeProjects.length)}
          color="blue"
        />
        <KPICard
          icon={<Building2 size={22} />}
          label="בהקמה"
          value={String(setupProjects.length)}
          color="amber"
        />
        <KPICard
          icon={<TrendingUp size={22} />}
          label='סה"כ יח"ד'
          value={String(projects.reduce((sum, p) => sum + (p.total_units || 0), 0))}
          color="green"
        />
        <KPICard
          icon={<ShieldCheck size={22} />}
          label="דוחות החודש"
          value="-"
          color="purple"
        />
      </div>

      {/* Project List */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="font-bold text-gray-900">פרויקטים</h2>
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
          <div className="divide-y divide-gray-50">
            {projects.map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                    <Building2 size={20} />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">{project.project_name}</h3>
                    <p className="text-sm text-gray-500">{project.city || "—"}</p>
                  </div>
                </div>

                <div className="flex items-center gap-6">
                  <div className="text-left">
                    <p className="text-sm text-gray-500">דוח נוכחי</p>
                    <p className="font-bold text-gray-900">#{project.current_report_number}</p>
                  </div>
                  <div className="text-left">
                    <p className="text-sm text-gray-500">יח&quot;ד</p>
                    <p className="font-bold text-gray-900">{project.total_units || "—"}</p>
                  </div>
                  <PhaseTag phase={project.phase} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function KPICard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: "blue" | "green" | "amber" | "purple";
}) {
  const colors = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-green-50 text-green-600",
    amber: "bg-amber-50 text-amber-600",
    purple: "bg-purple-50 text-purple-600",
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${colors[color]}`}>
          {icon}
        </div>
      </div>
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
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
