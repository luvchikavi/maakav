"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { FileDown, FileText, Download, ChevronRight, CheckCircle } from "lucide-react";
import api from "@/lib/api";

export default function GenerateStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    try {
      const response = await api.post(
        `/projects/${projectId}/monthly-reports/${reportId}/generate`,
        {},
        { responseType: "blob" }
      );

      // Download the file
      const blob = new Blob([response.data], {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;

      // Extract filename from header or use default
      const disposition = response.headers["content-disposition"];
      const filename = disposition
        ? disposition.split("filename=")[1]?.replace(/"/g, "")
        : `tracking_report_${reportId}.docx`;

      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setGenerated(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "שגיאה בהפקת הדוח");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center">
        {generated ? (
          <>
            <CheckCircle size={64} className="mx-auto text-green-500 mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">הדוח הופק בהצלחה!</h2>
            <p className="text-gray-500 mb-8">הקובץ הורד למחשב שלך</p>

            <button
              onClick={handleGenerate}
              className="px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition flex items-center justify-center gap-2 mx-auto"
            >
              <Download size={18} />
              הורד שוב
            </button>
          </>
        ) : (
          <>
            <FileDown size={56} className="mx-auto text-primary mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">הפקת דוח מעקב</h2>
            <p className="text-gray-500 mb-8">
              המערכת תייצר דוח Word בפורמט הסטנדרטי הבנקאי
            </p>

            <div className="bg-blue-50 rounded-xl p-6 mb-8 inline-block">
              <FileText size={32} className="mx-auto text-blue-600 mb-2" />
              <p className="font-medium text-gray-900">Word (.docx)</p>
              <p className="text-sm text-gray-500">ניתן לעריכה לפני שליחה לבנק</p>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-red-700 text-sm">
                {error}
              </div>
            )}

            <button
              onClick={handleGenerate}
              disabled={generating}
              className="w-full py-4 rounded-xl bg-primary text-white font-bold text-lg hover:bg-primary-dark transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {generating ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  מייצר דוח...
                </>
              ) : (
                <>
                  <Download size={22} />
                  הפק דוח מעקב
                </>
              )}
            </button>
          </>
        )}
      </div>

      <div className="flex justify-start mt-6">
        <button
          onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/review`)}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition"
        >
          <ChevronRight size={18} /> חזרה לסקירה
        </button>
      </div>
    </div>
  );
}
