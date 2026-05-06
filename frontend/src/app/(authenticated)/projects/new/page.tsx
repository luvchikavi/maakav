"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import api from "@/lib/api";

// Bank / financing body is captured on the project's financing-setup tab.
// Removed from this form to avoid duplicate input.

const ISRAELI_CITIES = [
  "ירושלים", "תל אביב-יפו", "חיפה", "ראשון לציון", "פתח תקווה", "אשדוד", "נתניה",
  "באר שבע", "בני ברק", "חולון", "רמת גן", "אשקלון", "רחובות", "בת ים", "הרצליה",
  "כפר סבא", "חדרה", "מודיעין-מכבים-רעות", "לוד", "נצרת", "רמלה", "רעננה",
  "הוד השרון", "גבעתיים", "קרית אתא", "נהריה", "עכו", "אילת", "קרית גת",
  "קרית מוצקין", "כרמיאל", "צפת", "טבריה", "עפולה", "נתיבות", "אור יהודה", "יבנה",
  "אור עקיבא", "ערד", "דימונה", "מגדל העמק", "שדרות", "קרית ביאליק", "קרית ים",
  "קרית שמונה", "ראש העין", "נס ציונה", "גבעת שמואל", "יהוד-מונוסון", "טירת כרמל",
  "מעלה אדומים", "ביתר עילית", "מודיעין עילית", "אלעד", "גני תקווה", "קדימה-צורן",
  "פרדס חנה-כרכור", "זכרון יעקב", "בנימינה-גבעת עדה", "עתלית", "חריש", "שוהם",
  "גדרה", "קרית עקרון", "באקה אל-גרבייה", "אום אל-פחם", "טייבה", "כפר קאסם",
  "סכנין", "מגאר", "שפרעם", "טמרה", "דאלית אל-כרמל", "ג'סר א-זרקא", "ג'לג'וליה",
  "קלנסווה", "רהט", "ירוחם", "מצפה רמון", "אופקים", "קרית מלאכי", "גן יבנה",
  "עומר", "להבים", "מיתר", "רמת ישי", "יוקנעם", "מבשרת ציון", "בית שמש",
  "בית שאן", "אריאל", "גבעת זאב",
];

const PROJECT_TYPES = [
  { value: "pinui_binui", label: "פינוי בינוי" },
  { value: "land", label: "רכישת קרקע" },
  { value: "combination", label: "קומבינציה" },
  { value: "tama38", label: 'תמ"א 38' },
  { value: "other", label: "אחר" },
];

export default function NewProjectPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    project_name: "",
    address: "",
    city: "",
    developer_name: "",
    project_type: "",
  });

  const set = (field: string, value: string) => setForm((p) => ({ ...p, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.project_name.trim()) {
      setError("שם הפרויקט הוא שדה חובה");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/projects", form);
      router.push(`/projects/${data.id}`);
    } catch {
      setError("שגיאה ביצירת הפרויקט");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Back */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-6 transition"
      >
        <ArrowRight size={18} />
        חזרה
      </button>

      <h1 className="text-2xl font-bold text-gray-900 mb-2">פרויקט חדש</h1>
      <p className="text-gray-500 mb-8">הזן את הפרטים הבסיסיים. שאר הנתונים יוזנו בשלב ההגדרה.</p>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-gray-200 p-8 space-y-6">
        {error && (
          <div className="p-3 rounded-xl bg-red-50 text-red-700 text-sm">{error}</div>
        )}

        <Field label="שם הפרויקט *" value={form.project_name} onChange={(v) => set("project_name", v)} placeholder='לדוגמה: רש"י 12 רמת גן' />
        <div className="grid grid-cols-2 gap-4">
          <Field label="כתובת" value={form.address} onChange={(v) => set("address", v)} placeholder={"רח' רש\"י 12"} />
          <CityAutocomplete value={form.city} onChange={(v) => set("city", v)} />
        </div>
        <Field label="שם היזם" value={form.developer_name} onChange={(v) => set("developer_name", v)} placeholder='נווה שוסטר בע"מ' />

        <SelectField label="סוג פרויקט" value={form.project_type} onChange={(v) => set("project_type", v)} options={PROJECT_TYPES} />
        {/* Bank / financing-body is set on the financing setup tab — no need to pick it twice. */}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 rounded-xl bg-primary text-white font-medium hover:bg-primary-dark transition disabled:opacity-50"
        >
          {loading ? "יוצר פרויקט..." : "צור פרויקט"}
        </button>
      </form>
    </div>
  );
}

function Field({
  label, value, onChange, placeholder, dir,
}: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; dir?: string;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        dir={dir}
        className="w-full px-4 py-3 rounded-xl border border-gray-200 text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
      />
    </div>
  );
}

function SelectField({
  label, value, onChange, options,
}: {
  label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[];
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-3 rounded-xl border border-gray-200 text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
      >
        <option value="">בחר...</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

function CityAutocomplete({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const filtered =
    value.length >= 1
      ? ISRAELI_CITIES.filter((c) => c.includes(value)).slice(0, 8)
      : [];

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <label className="block text-sm font-medium text-gray-700 mb-1.5">עיר</label>
      <input
        type="text"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => {
          if (value.length >= 1) setOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
        placeholder="רמת גן"
        className="w-full px-4 py-3 rounded-xl border border-gray-200 text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
      />
      {open && filtered.length > 0 && (
        <ul className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg max-h-64 overflow-y-auto">
          {filtered.map((city) => (
            <li
              key={city}
              onMouseDown={() => {
                onChange(city);
                setOpen(false);
              }}
              className="px-4 py-2.5 text-gray-900 cursor-pointer hover:bg-gray-50 transition first:rounded-t-xl last:rounded-b-xl"
            >
              {city}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
