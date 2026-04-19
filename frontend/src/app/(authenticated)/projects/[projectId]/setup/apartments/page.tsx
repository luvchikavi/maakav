"use client";

import { useState, useCallback, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Upload, Building2, CheckCircle, Trash2, Filter, X } from "lucide-react";
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
  owner_name: string | null;
  include_in_revenue: boolean;
}

const OWNERSHIP_LABELS: Record<string, string> = { developer: "יזם", resident: "דיירים" };
const STATUS_LABELS: Record<string, string> = {
  for_sale: "לשיווק", sold: "נמכר", compensation: "תמורה",
  for_rent: "להשכרה", reserved: "שמור", inventory: "מלאי",
};
const TYPE_LABELS: Record<string, string> = {
  apartment: "דירה", penthouse: "פנטהאוז", garden: "גן", duplex: "דופלקס",
  duplex_garden: "דופלקס גן", duplex_roof: "דופלקס גג", mini_penthouse: "מיני פנטהאוז",
  office: "משרד", retail: "מסחר", storage: "מחסן", parking: "חניה", other: "אחר",
};

const RESIDENTIAL_TYPES = new Set(["apartment", "penthouse", "garden", "duplex", "duplex_garden", "duplex_roof", "mini_penthouse"]);

type FilterMode = "all" | "developer_residential" | "developer_commercial" | "resident_residential" | "resident_commercial";

const FILTER_OPTIONS: { value: FilterMode; label: string }[] = [
  { value: "all", label: "הכל" },
  { value: "developer_residential", label: "מגורים יזם" },
  { value: "developer_commercial", label: "מסחרי יזם" },
  { value: "resident_residential", label: "מגורים בעלים" },
  { value: "resident_commercial", label: "מסחרי בעלים" },
];

export default function ApartmentsSetupPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ imported: number } | null>(null);
  const [filter, setFilter] = useState<FilterMode>("all");

  const { data: apartments = [] } = useQuery<Apartment[]>({
    queryKey: ["apartments", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/setup/apartments`)).data,
  });

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setUploadResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post(`/projects/${projectId}/setup/apartments/upload`, formData);
      setUploadResult({ imported: data.imported });
      queryClient.invalidateQueries({ queryKey: ["apartments", projectId] });
      queryClient.invalidateQueries({ queryKey: ["setup-status", projectId] });
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "שגיאה בהעלאת הקובץ");
    } finally {
      setUploading(false);
    }
  }, [projectId, queryClient]);

  const handleDelete = async (id: number) => {
    if (!confirm("למחוק יחידה זו?")) return;
    await api.delete(`/projects/${projectId}/setup/apartments/${id}`);
    queryClient.invalidateQueries({ queryKey: ["apartments", projectId] });
  };

  // Filtered apartments
  const filtered = useMemo(() => {
    return apartments.filter((a) => {
      const isResidential = RESIDENTIAL_TYPES.has(a.unit_type);
      switch (filter) {
        case "developer_residential": return a.ownership === "developer" && isResidential;
        case "developer_commercial": return a.ownership === "developer" && !isResidential;
        case "resident_residential": return a.ownership === "resident" && isResidential;
        case "resident_commercial": return a.ownership === "resident" && !isResidential;
        default: return true;
      }
    });
  }, [apartments, filter]);

  // Counts
  const devRes = apartments.filter((a) => a.ownership === "developer" && RESIDENTIAL_TYPES.has(a.unit_type)).length;
  const devCom = apartments.filter((a) => a.ownership === "developer" && !RESIDENTIAL_TYPES.has(a.unit_type)).length;
  const resRes = apartments.filter((a) => a.ownership === "resident" && RESIDENTIAL_TYPES.has(a.unit_type)).length;
  const resCom = apartments.filter((a) => a.ownership === "resident" && !RESIDENTIAL_TYPES.has(a.unit_type)).length;

  return (
    <div>
      <button onClick={() => router.push(`/projects/${projectId}`)} className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-4 transition">
        <ArrowRight size={18} /> חזרה לפרויקט
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">מלאי דירות ונכסים</h1>
          <p className="text-gray-500 mt-1">יחידות דיור ומסחר - יזם ובעלים</p>
        </div>
        {apartments.length > 0 && (
          <div className="flex gap-2">
            <div className="text-center px-3 py-1.5 bg-blue-50 rounded-lg">
              <p className="text-sm font-bold text-blue-700">{devRes}</p>
              <p className="text-[10px] text-blue-600">מגורים יזם</p>
            </div>
            <div className="text-center px-3 py-1.5 bg-blue-50/50 rounded-lg">
              <p className="text-sm font-bold text-blue-600">{devCom}</p>
              <p className="text-[10px] text-blue-500">מסחרי יזם</p>
            </div>
            <div className="text-center px-3 py-1.5 bg-amber-50 rounded-lg">
              <p className="text-sm font-bold text-amber-700">{resRes}</p>
              <p className="text-[10px] text-amber-600">מגורים בעלים</p>
            </div>
            <div className="text-center px-3 py-1.5 bg-amber-50/50 rounded-lg">
              <p className="text-sm font-bold text-amber-600">{resCom}</p>
              <p className="text-[10px] text-amber-500">מסחרי בעלים</p>
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
            <span>העלאת קובץ Excel עם מלאי</span>
          </div>
        )}
      </div>

      {/* Filter bar */}
      {apartments.length > 0 && (
        <div className="flex items-center gap-2 mb-4">
          <Filter size={16} className="text-gray-400" />
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setFilter(opt.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                filter === opt.value
                  ? "bg-primary text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {opt.label}
            </button>
          ))}
          {filter !== "all" && (
            <span className="text-xs text-gray-400 mr-2">
              {filtered.length} מתוך {apartments.length}
            </span>
          )}
        </div>
      )}

      {/* Table */}
      {filtered.length > 0 && (
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
                  <th className="text-right px-4 py-3 font-medium">סטטוס / בעלים</th>
                  <th className="text-left px-4 py-3 font-medium">שווי כולל מע&quot;מ</th>
                  <th className="px-4 py-3 w-10" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map((apt) => (
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
                    <td className="px-4 py-3 text-gray-600">
                      {apt.ownership === "resident" && apt.owner_name
                        ? apt.owner_name
                        : STATUS_LABELS[apt.unit_status] || apt.unit_status}
                    </td>
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

      {apartments.length > 0 && filtered.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <p>אין נכסים מתאימים לסינון שנבחר</p>
        </div>
      )}
    </div>
  );
}
