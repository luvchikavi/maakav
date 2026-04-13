"use client";

import { useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Upload, Building2, CheckCircle, Trash2 } from "lucide-react";
import api from "@/lib/api";
import { formatCurrency } from "@/lib/formatters";

interface Apartment {
  id: number;
  building_number: string;
  floor: string | null;
  unit_number: string | null;
  unit_type: string;
  ownership: string;
  unit_status: string;
  room_count: number | null;
  net_area_sqm: number | null;
  list_price_with_vat: number | null;
  list_price_no_vat: number | null;
  include_in_revenue: boolean;
}

const OWNERSHIP_LABELS: Record<string, string> = { developer: "יזם", resident: "דיירים" };
const STATUS_LABELS: Record<string, string> = { for_sale: "לשיווק", sold: "נמכר", compensation: "תמורה", for_rent: "להשכרה" };
const TYPE_LABELS: Record<string, string> = {
  apartment: "דירה", penthouse: "פנטהאוז", garden: "גן", duplex: "דופלקס",
  office: "משרד", retail: "מסחר", storage: "מחסן", parking: "חניה", other: "אחר",
};

export default function ApartmentsSetupPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ imported: number } | null>(null);

  const { data: apartments = [], isLoading } = useQuery<Apartment[]>({
    queryKey: ["apartments", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/setup/apartments`)).data,
  });

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setUploadResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post(`/projects/${projectId}/setup/apartments/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadResult({ imported: data.imported });
      queryClient.invalidateQueries({ queryKey: ["apartments", projectId] });
      queryClient.invalidateQueries({ queryKey: ["setup-status", projectId] });
    } catch (err: any) {
      alert(err?.response?.data?.detail || "שגיאה בהעלאת הקובץ");
    } finally {
      setUploading(false);
    }
  }, [projectId, queryClient]);

  const handleDelete = async (id: number) => {
    if (!confirm("למחוק יחידה זו?")) return;
    await api.delete(`/projects/${projectId}/setup/apartments/${id}`);
    queryClient.invalidateQueries({ queryKey: ["apartments", projectId] });
  };

  const developerUnits = apartments.filter((a) => a.ownership === "developer");
  const residentUnits = apartments.filter((a) => a.ownership === "resident");

  return (
    <div>
      <button onClick={() => router.push(`/projects/${projectId}`)} className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4 transition">
        <ArrowRight size={18} /> חזרה לפרויקט
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">מלאי דירות</h1>
          <p className="text-gray-500 mt-1">יחידות דיור - יזם ובעלים/דיירים</p>
        </div>
        {apartments.length > 0 && (
          <div className="flex gap-3">
            <div className="text-center px-4 py-2 bg-blue-50 rounded-xl">
              <p className="text-lg font-bold text-blue-700">{developerUnits.length}</p>
              <p className="text-xs text-blue-600">יזם</p>
            </div>
            <div className="text-center px-4 py-2 bg-amber-50 rounded-xl">
              <p className="text-lg font-bold text-amber-700">{residentUnits.length}</p>
              <p className="text-xs text-amber-600">דיירים</p>
            </div>
          </div>
        )}
      </div>

      {/* Upload */}
      <div
        className="bg-white rounded-2xl border-2 border-dashed border-gray-200 hover:border-primary/40 p-6 text-center mb-6 cursor-pointer transition"
        onClick={() => {
          const input = document.createElement("input");
          input.type = "file";
          input.accept = ".xlsx,.xls";
          input.onchange = (e) => {
            const file = (e.target as HTMLInputElement).files?.[0];
            if (file) handleUpload(file);
          };
          input.click();
        }}
      >
        {uploading ? (
          <div className="flex items-center justify-center gap-3">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-gray-600">מעבד קובץ...</span>
          </div>
        ) : uploadResult ? (
          <div className="flex items-center justify-center gap-2 text-green-600">
            <CheckCircle size={20} />
            <span className="font-medium">יובאו {uploadResult.imported} יחידות</span>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-2 text-gray-500">
            <Upload size={20} />
            <span>העלאת קובץ Excel עם מלאי דירות</span>
          </div>
        )}
      </div>

      {/* Table */}
      {apartments.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-500 bg-gray-50 border-b">
                  <th className="text-right px-4 py-3 font-medium">בניין</th>
                  <th className="text-right px-4 py-3 font-medium">קומה</th>
                  <th className="text-right px-4 py-3 font-medium">מס&apos;ד</th>
                  <th className="text-right px-4 py-3 font-medium">סוג</th>
                  <th className="text-right px-4 py-3 font-medium">חדרים</th>
                  <th className="text-right px-4 py-3 font-medium">שטח</th>
                  <th className="text-right px-4 py-3 font-medium">בעלות</th>
                  <th className="text-right px-4 py-3 font-medium">סטטוס</th>
                  <th className="text-left px-4 py-3 font-medium">שווי כולל מע&quot;מ</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {apartments.map((apt) => (
                  <tr key={apt.id} className="hover:bg-gray-50/50 transition text-sm">
                    <td className="px-4 py-3 text-gray-900">{apt.building_number}</td>
                    <td className="px-4 py-3 text-gray-900">{apt.floor || "—"}</td>
                    <td className="px-4 py-3 text-gray-900">{apt.unit_number || "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{TYPE_LABELS[apt.unit_type] || apt.unit_type}</td>
                    <td className="px-4 py-3 text-gray-600">{apt.room_count || "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{apt.net_area_sqm ? `${apt.net_area_sqm} מ"ר` : "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        apt.ownership === "developer" ? "bg-blue-50 text-blue-700" : "bg-amber-50 text-amber-700"
                      }`}>
                        {OWNERSHIP_LABELS[apt.ownership]}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{STATUS_LABELS[apt.unit_status] || apt.unit_status}</td>
                    <td className="px-4 py-3 text-left font-medium text-gray-900">
                      {apt.list_price_with_vat ? formatCurrency(Number(apt.list_price_with_vat)) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <button onClick={() => handleDelete(apt.id)} className="text-gray-300 hover:text-red-500 transition">
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
