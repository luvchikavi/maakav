"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { FileDown, FileText, Download, ChevronRight } from "lucide-react";

export default function GenerateStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();
  const [generating, setGenerating] = useState(false);

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center">
        <FileDown size={56} className="mx-auto text-primary mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">הפקת דוח מעקב</h2>
        <p className="text-gray-500 mb-8">המערכת תייצר דוח Word + PDF בפורמט הסטנדרטי הבנקאי</p>

        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="bg-blue-50 rounded-xl p-6">
            <FileText size={32} className="mx-auto text-blue-600 mb-2" />
            <p className="font-medium text-gray-900">Word (.docx)</p>
            <p className="text-sm text-gray-500">ניתן לעריכה לפני שליחה</p>
          </div>
          <div className="bg-red-50 rounded-xl p-6">
            <FileText size={32} className="mx-auto text-red-600 mb-2" />
            <p className="font-medium text-gray-900">PDF</p>
            <p className="text-sm text-gray-500">סופי לשליחה לבנק</p>
          </div>
        </div>

        <button
          onClick={async () => {
            setGenerating(true);
            // TODO: Call generate endpoint
            setTimeout(() => setGenerating(false), 2000);
          }}
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

        <p className="text-sm text-gray-400 mt-4">
          הפקת הדוח תופעל בשלב 5 של הפיתוח (report generation engine)
        </p>
      </div>

      <div className="flex justify-start mt-6">
        <button onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/review`)}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition">
          <ChevronRight size={18} /> חזרה לסקירה
        </button>
      </div>
    </div>
  );
}
