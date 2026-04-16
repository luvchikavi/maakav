"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Save, CheckCircle, TrendingUp, RefreshCw, AlertCircle } from "lucide-react";
import api from "@/lib/api";

interface CBSIndex {
  index_value: number;
  period: string;
  period_display: string;
  source: string;
}

export default function IndexStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [indexValue, setIndexValue] = useState("");

  const { data: report } = useQuery({
    queryKey: ["report", reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}`)).data,
  });

  const { data: project } = useQuery({
    queryKey: ["project", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}`)).data,
  });

  // Auto-fetch latest CBS index
  const { data: cbsIndex, isLoading: cbsLoading, error: cbsError, refetch: refetchCbs } = useQuery<CBSIndex>({
    queryKey: ["cbs-index", projectId, reportId],
    queryFn: async () => (await api.get(`/projects/${projectId}/monthly-reports/${reportId}/index/latest`)).data,
    retry: false,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  useEffect(() => {
    if (report?.current_index) setIndexValue(report.current_index.toString());
  }, [report]);

  const mutation = useMutation({
    mutationFn: async () => {
      return api.patch(`/projects/${projectId}/monthly-reports/${reportId}/index?current_index=${indexValue}`);
    },
    onSuccess: () => {
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      queryClient.invalidateQueries({ queryKey: ["report", reportId] });
      queryClient.invalidateQueries({ queryKey: ["completeness", reportId] });
    },
  });

  const applyCbsIndex = () => {
    if (cbsIndex?.index_value) {
      setIndexValue(cbsIndex.index_value.toString());
    }
  };

  return (
    <div className="max-w-lg mx-auto">
      <div className="bg-white rounded-2xl border border-gray-200 p-8 space-y-6">
        <div className="flex items-center gap-3 mb-2">
          <TrendingUp size={24} className="text-primary" />
          <h2 className="text-lg font-bold text-gray-900">עדכון מדד תשומות בנייה</h2>
        </div>

        {/* CBS Auto-fetch Card */}
        <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-blue-800">מדד אחרון מהלמ&quot;ס</p>
            <button
              onClick={() => refetchCbs()}
              disabled={cbsLoading}
              className="text-blue-600 hover:text-blue-800 transition"
              title="רענון"
            >
              <RefreshCw size={16} className={cbsLoading ? "animate-spin" : ""} />
            </button>
          </div>

          {cbsLoading && (
            <p className="text-sm text-blue-600">טוען מדד עדכני...</p>
          )}

          {cbsError && (
            <div className="flex items-center gap-2 text-sm text-amber-700">
              <AlertCircle size={14} />
              <span>לא ניתן לטעון מדד אוטומטית — יש להזין ידנית</span>
            </div>
          )}

          {cbsIndex && (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-blue-900">{cbsIndex.index_value}</p>
                  <p className="text-xs text-blue-600">{cbsIndex.period_display} &middot; {cbsIndex.source}</p>
                </div>
                <button
                  onClick={applyCbsIndex}
                  className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg font-medium hover:bg-blue-700 transition"
                >
                  אשר והחל
                </button>
              </div>
            </>
          )}
        </div>

        {project?.base_index && (
          <div className="bg-gray-50 rounded-xl p-4">
            <p className="text-sm text-gray-500">מדד בסיס (דוח אפס)</p>
            <p className="text-xl font-bold text-gray-900">{project.base_index}</p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">מדד תשומות בנייה נוכחי</label>
          <input
            type="number"
            step="0.1"
            value={indexValue}
            onChange={(e) => setIndexValue(e.target.value)}
            placeholder="לדוגמה: 138.4"
            dir="ltr"
            className="w-full px-4 py-4 rounded-xl border border-gray-200 text-2xl font-bold text-center focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>

        {project?.base_index && indexValue && (
          <div className="bg-primary/5 rounded-xl p-4 text-center">
            <p className="text-sm text-gray-500">יחס מדדים</p>
            <p className="text-xl font-bold text-primary">
              {(parseFloat(indexValue) / parseFloat(project.base_index) * 100).toFixed(1)}%
            </p>
          </div>
        )}

        <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !indexValue}
          className="w-full py-3 rounded-xl bg-primary text-white font-medium hover:bg-primary-dark transition disabled:opacity-50 flex items-center justify-center gap-2">
          {saved ? <><CheckCircle size={18} /> נשמר</> : <><Save size={18} /> שמור</>}
        </button>
      </div>

      <div className="flex justify-between mt-6">
        <button onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/construction`)}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition">
          <ChevronRight size={18} /> חזרה
        </button>
        <button onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/guarantees`)}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition">
          המשך לערבויות <ChevronLeft size={18} />
        </button>
      </div>
    </div>
  );
}
