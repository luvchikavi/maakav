"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Save, CheckCircle } from "lucide-react";
import api from "@/lib/api";

export default function ConstructionStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState({ overall_percent: "", description_text: "", visitor_name: "" });

  const { data } = useQuery({
    queryKey: ["construction", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/construction`)).data,
  });

  useEffect(() => {
    if (data) {
      setForm({
        overall_percent: data.overall_percent?.toString() || "",
        description_text: data.description_text || "",
        visitor_name: data.visitor_name || "",
      });
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: async () => {
      return api.put(`/projects/${projectId}/monthly-reports/${reportId}/construction`, {
        overall_percent: parseFloat(form.overall_percent) || 0,
        description_text: form.description_text,
        visitor_name: form.visitor_name,
      });
    },
    onSuccess: () => {
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      queryClient.invalidateQueries({ queryKey: ["completeness", reportId] });
    },
  });

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-2xl border border-gray-200 p-8 space-y-6">
        <h2 className="text-lg font-bold text-gray-900">התקדמות בנייה</h2>

        {/* Progress slider */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">אחוז ביצוע מצטבר</label>
            <span className="text-2xl font-bold text-primary">{form.overall_percent || 0}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            step="0.5"
            value={form.overall_percent || 0}
            onChange={(e) => setForm((p) => ({ ...p, overall_percent: e.target.value }))}
            className="w-full h-3 rounded-full appearance-none bg-gray-200 accent-primary"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>0%</span>
            <span>25%</span>
            <span>50%</span>
            <span>75%</span>
            <span>100%</span>
          </div>
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">תיאור עבודות שבוצעו</label>
          <textarea
            value={form.description_text}
            onChange={(e) => setForm((p) => ({ ...p, description_text: e.target.value }))}
            rows={5}
            placeholder="באתר מבוצעות עבודות שלד, אינסטלציה וחשמל בבניין A..."
            className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>

        {/* Visitor */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">שם עורך הביקור</label>
          <input
            type="text"
            value={form.visitor_name}
            onChange={(e) => setForm((p) => ({ ...p, visitor_name: e.target.value }))}
            className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>

        <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
          className="w-full py-3 rounded-xl bg-primary text-white font-medium hover:bg-primary-dark transition disabled:opacity-50 flex items-center justify-center gap-2">
          {saved ? <><CheckCircle size={18} /> נשמר</> : mutation.isPending ? "שומר..." : <><Save size={18} /> שמור</>}
        </button>
      </div>

      {/* Navigation */}
      <div className="flex justify-between mt-6">
        <button onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/sales`)}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition">
          <ChevronRight size={18} /> חזרה למכירות
        </button>
        <button onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/index`)}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition">
          המשך למדד <ChevronLeft size={18} />
        </button>
      </div>
    </div>
  );
}
