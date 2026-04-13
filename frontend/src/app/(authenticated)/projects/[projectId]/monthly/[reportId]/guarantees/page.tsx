"use client";

import { useParams, useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Shield, Upload } from "lucide-react";

export default function GuaranteesStep() {
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();
  const router = useRouter();

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-2xl border border-gray-200 p-8">
        <div className="flex items-center gap-3 mb-6">
          <Shield size={24} className="text-primary" />
          <h2 className="text-lg font-bold text-gray-900">ערבויות</h2>
        </div>

        <div
          className="border-2 border-dashed border-gray-200 hover:border-primary/40 rounded-xl p-8 text-center cursor-pointer transition"
          onClick={() => {
            const input = document.createElement("input");
            input.type = "file";
            input.accept = ".pdf,.xlsx,.xls";
            input.click();
          }}
        >
          <Upload size={36} className="mx-auto text-gray-400 mb-3" />
          <p className="text-gray-700 font-medium">העלה תדפיס ערבויות</p>
          <p className="text-gray-400 text-sm mt-1">PDF או Excel</p>
        </div>

        <p className="text-sm text-gray-500 bg-gray-50 rounded-xl p-4 mt-6">
          שלב זה אופציונלי. ניתן להמשיך לסקירה גם ללא העלאת ערבויות.
        </p>
      </div>

      <div className="flex justify-between mt-6">
        <button onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/index`)}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition">
          <ChevronRight size={18} /> חזרה
        </button>
        <button onClick={() => router.push(`/projects/${projectId}/monthly/${reportId}/review`)}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition">
          המשך לסקירה <ChevronLeft size={18} />
        </button>
      </div>
    </div>
  );
}
