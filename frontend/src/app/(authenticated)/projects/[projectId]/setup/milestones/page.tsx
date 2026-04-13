"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Plus, Trash2, CheckCircle, Flag } from "lucide-react";
import api from "@/lib/api";
import { formatDate } from "@/lib/formatters";

interface Milestone {
  id: number;
  name: string;
  planned_date: string | null;
  actual_date: string | null;
  display_order: number;
}

const DEFAULT_MILESTONES = [
  "קבלת היתר בנייה",
  "תחילת ביצוע",
  "יציקת יסודות",
  "סיום שלד",
  "טופס 4",
  "תעודת גמר",
];

export default function MilestonesSetupPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [newName, setNewName] = useState("");

  const { data: milestones = [] } = useQuery<Milestone[]>({
    queryKey: ["milestones", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/setup/milestones`)).data,
  });

  const addMutation = useMutation({
    mutationFn: async (name: string) => {
      return api.post(`/projects/${projectId}/setup/milestones`, {
        name,
        display_order: milestones.length,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["milestones", projectId] });
      queryClient.invalidateQueries({ queryKey: ["setup-status", projectId] });
      setNewName("");
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, ...data }: { id: number; planned_date?: string; actual_date?: string }) => {
      return api.patch(`/projects/${projectId}/setup/milestones/${id}`, data);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["milestones", projectId] }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/projects/${projectId}/setup/milestones/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["milestones", projectId] });
      queryClient.invalidateQueries({ queryKey: ["setup-status", projectId] });
    },
  });

  const addDefaults = async () => {
    for (const name of DEFAULT_MILESTONES) {
      if (!milestones.some((m) => m.name === name)) {
        await api.post(`/projects/${projectId}/setup/milestones`, { name, display_order: milestones.length });
      }
    }
    queryClient.invalidateQueries({ queryKey: ["milestones", projectId] });
    queryClient.invalidateQueries({ queryKey: ["setup-status", projectId] });
  };

  return (
    <div className="max-w-2xl mx-auto">
      <button onClick={() => router.push(`/projects/${projectId}`)} className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4 transition">
        <ArrowRight size={18} /> חזרה לפרויקט
      </button>

      <h1 className="text-2xl font-bold text-gray-900 mb-2">אבני דרך</h1>
      <p className="text-gray-500 mb-6">לוחות זמנים - מתוכנן מול בפועל</p>

      {/* Quick add defaults */}
      {milestones.length === 0 && (
        <button onClick={addDefaults}
          className="w-full mb-6 py-4 rounded-2xl border-2 border-dashed border-primary/30 text-primary font-medium hover:bg-primary/5 transition flex items-center justify-center gap-2">
          <Flag size={20} />
          הוסף אבני דרך סטנדרטיות (היתר, יסודות, שלד, טופס 4...)
        </button>
      )}

      {/* Milestones list */}
      <div className="space-y-3 mb-6">
        {milestones.map((ms) => (
          <div key={ms.id} className="bg-white rounded-2xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {ms.actual_date ? (
                  <CheckCircle size={18} className="text-green-500" />
                ) : (
                  <Flag size={18} className="text-gray-400" />
                )}
                <span className="font-bold text-gray-900">{ms.name}</span>
              </div>
              <button onClick={() => deleteMutation.mutate(ms.id)} className="text-gray-300 hover:text-red-500 transition">
                <Trash2 size={16} />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1">תאריך מתוכנן</label>
                <input
                  type="date"
                  value={ms.planned_date || ""}
                  onChange={(e) => updateMutation.mutate({ id: ms.id, planned_date: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  dir="ltr"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">תאריך בפועל</label>
                <input
                  type="date"
                  value={ms.actual_date || ""}
                  onChange={(e) => updateMutation.mutate({ id: ms.id, actual_date: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  dir="ltr"
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Add new */}
      <div className="flex gap-3">
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="שם אבן דרך חדשה..."
          className="flex-1 px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          onKeyDown={(e) => {
            if (e.key === "Enter" && newName.trim()) addMutation.mutate(newName.trim());
          }}
        />
        <button
          onClick={() => newName.trim() && addMutation.mutate(newName.trim())}
          disabled={!newName.trim()}
          className="px-5 py-3 rounded-xl bg-primary text-white font-medium hover:bg-primary-dark transition disabled:opacity-50 flex items-center gap-2"
        >
          <Plus size={18} /> הוסף
        </button>
      </div>
    </div>
  );
}
