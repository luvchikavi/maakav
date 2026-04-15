"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { FileDown, FileText, Download, ChevronRight, CheckCircle, FileType } from "lucide-react";
import api from "@/lib/api";

export default function GenerateStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [error, setError] = useState("");
  const [lastFormat, setLastFormat] = useState<"docx" | "pdf">("docx");

  const { data: pdfStatus } = useQuery({
    queryKey: ["pdf-available"],
    queryFn: async () => (await api.get("/reports/pdf-available")).data,
    staleTime: 60_000,
  });

  const pdfAvailable = pdfStatus?.available === true;

  const handleGenerate = async (format: "docx" | "pdf") => {
    setGenerating(true);
    setError("");
    setLastFormat(format);
    try {
      const response = await api.post(
        `/projects/${projectId}/monthly-reports/${reportId}/generate?format=${format}`,
        {},
        { responseType: "blob" }
      );

      const mimeType = format === "pdf"
        ? "application/pdf"
        : "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

      const blob = new Blob([response.data], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;

      const disposition = response.headers["content-disposition"];
      const filename = disposition
        ? disposition.split("filename=")[1]?.replace(/"/g, "")
        : `tracking_report_${reportId}.${format}`;

      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setGenerated(true);
    } catch (err: any) {
      if (err?.response?.data instanceof Blob) {
        const text = await err.response.data.text();
        try {
          const json = JSON.parse(text);
          setError(json.detail || "שגיאה בהפקת הדוח");
        } catch {
          setError("שגיאה בהפקת הדוח");
        }
      } else {
        setError(err?.response?.data?.detail || "שגיאה בהפקת הדוח");
      }
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
            <p className="text-gray-500 mb-8">הקובץ הורד למחשב שלך ({lastFormat.toUpperCase()})</p>

            <div className="flex gap-3 justify-center">
              <button
                onClick={() => handleGenerate("docx")}
                disabled={generating}
                className="px-5 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition flex items-center gap-2 disabled:opacity-50"
              >
                <FileText size={18} /> הורד Word
              </button>
              <button
                onClick={() => handleGenerate("pdf")}
                disabled={generating || !pdfAvailable}
                className="px-5 py-3 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 transition flex items-center gap-2 disabled:opacity-50"
                title={!pdfAvailable ? "PDF לא זמין — LibreOffice לא מותקן" : ""}
              >
                <FileType size={18} /> הורד PDF
              </button>
            </div>
          </>
        ) : (
          <>
            <FileDown size={56} className="mx-auto text-primary mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">הפקת דוח מעקב</h2>
            <p className="text-gray-500 mb-8">
              המערכת תייצר דוח בפורמט הסטנדרטי הבנקאי
            </p>

            <div className="flex gap-4 justify-center mb-8">
              <div className="bg-blue-50 rounded-xl p-6 flex-1 max-w-[200px]">
                <FileText size={32} className="mx-auto text-blue-600 mb-2" />
                <p className="font-medium text-gray-900">Word (.docx)</p>
                <p className="text-xs text-gray-500 mt-1">ניתן לעריכה</p>
              </div>
              <div className={`rounded-xl p-6 flex-1 max-w-[200px] ${pdfAvailable ? "bg-red-50" : "bg-gray-50"}`}>
                <FileType size={32} className={`mx-auto mb-2 ${pdfAvailable ? "text-red-600" : "text-gray-400"}`} />
                <p className={`font-medium ${pdfAvailable ? "text-gray-900" : "text-gray-400"}`}>PDF</p>
                <p className="text-xs text-gray-500 mt-1">
                  {pdfAvailable ? "מוכן לשליחה" : "LibreOffice לא מותקן"}
                </p>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-red-700 text-sm">
                {error}
              </div>
            )}

            <div className="flex gap-3 justify-center">
              <button
                onClick={() => handleGenerate("docx")}
                disabled={generating}
                className="flex-1 max-w-[240px] py-4 rounded-xl bg-blue-600 text-white font-bold text-lg hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {generating && lastFormat === "docx" ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    מייצר...
                  </>
                ) : (
                  <>
                    <Download size={20} /> Word
                  </>
                )}
              </button>
              <button
                onClick={() => handleGenerate("pdf")}
                disabled={generating || !pdfAvailable}
                className="flex-1 max-w-[240px] py-4 rounded-xl bg-red-600 text-white font-bold text-lg hover:bg-red-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {generating && lastFormat === "pdf" ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    מייצר...
                  </>
                ) : (
                  <>
                    <Download size={20} /> PDF
                  </>
                )}
              </button>
            </div>
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
