"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Users, Plus, Trash2, Shield, Eye, PenTool, X, KeyRound } from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface UserItem {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
}

const ROLE_LABELS: Record<string, string> = {
  admin: "מנהל",
  appraiser: "שמאי",
  viewer: "צפייה בלבד",
};

const ROLE_ICONS: Record<string, React.ReactNode> = {
  admin: <Shield size={14} />,
  appraiser: <PenTool size={14} />,
  viewer: <Eye size={14} />,
};

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-red-100 text-red-700",
  appraiser: "bg-blue-100 text-blue-700",
  viewer: "bg-gray-100 text-gray-700",
};

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const qc = useQueryClient();
  const [showInvite, setShowInvite] = useState(false);
  const [resetUserId, setResetUserId] = useState<number | null>(null);

  const isAdmin = currentUser?.role === "admin" || currentUser?.role === "ADMIN";

  const { data: users = [] } = useQuery<UserItem[]>({
    queryKey: ["users"],
    queryFn: async () => (await api.get("/users")).data,
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: number) => api.delete(`/users/${userId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ userId, isActive }: { userId: number; isActive: boolean }) =>
      api.patch(`/users/${userId}`, { is_active: isActive }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: number; role: string }) =>
      api.patch(`/users/${userId}`, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Users size={24} className="text-primary" />
          <h1 className="text-2xl font-bold text-gray-900">ניהול משתמשים</h1>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowInvite(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-xl text-sm font-medium hover:bg-primary-dark transition"
          >
            <Plus size={16} /> הוסף משתמש
          </button>
        )}
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="text-xs text-gray-500 bg-gray-50 border-b">
              <th className="text-right px-4 py-3 font-medium">שם</th>
              <th className="text-right px-4 py-3 font-medium">אימייל</th>
              <th className="text-center px-4 py-3 font-medium">תפקיד</th>
              <th className="text-center px-4 py-3 font-medium">סטטוס</th>
              {isAdmin && <th className="text-center px-4 py-3 font-medium w-28">פעולות</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {users.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50/50 transition">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary shrink-0">
                      {u.first_name[0]}
                    </div>
                    <span className="text-sm font-medium text-gray-900">
                      {u.first_name} {u.last_name}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-gray-600" dir="ltr">{u.email}</td>
                <td className="px-4 py-3 text-center">
                  {isAdmin && u.id !== currentUser?.id ? (
                    <select
                      value={u.role}
                      onChange={(e) => updateRoleMutation.mutate({ userId: u.id, role: e.target.value })}
                      className={`px-2 py-1 rounded-lg text-xs font-medium border-0 cursor-pointer ${ROLE_COLORS[u.role] || ROLE_COLORS.viewer}`}
                    >
                      <option value="admin">מנהל</option>
                      <option value="appraiser">שמאי</option>
                      <option value="viewer">צפייה בלבד</option>
                    </select>
                  ) : (
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium ${ROLE_COLORS[u.role] || ROLE_COLORS.viewer}`}>
                      {ROLE_ICONS[u.role]} {ROLE_LABELS[u.role] || u.role}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  {isAdmin && u.id !== currentUser?.id ? (
                    <button
                      onClick={() => toggleActiveMutation.mutate({ userId: u.id, isActive: !u.is_active })}
                      className={`px-2 py-1 rounded-lg text-xs font-medium ${
                        u.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                      }`}
                    >
                      {u.is_active ? "פעיל" : "מושבת"}
                    </button>
                  ) : (
                    <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                      u.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                    }`}>
                      {u.is_active ? "פעיל" : "מושבת"}
                    </span>
                  )}
                </td>
                {isAdmin && (
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        onClick={() => setResetUserId(u.id)}
                        className="text-gray-400 hover:text-blue-500 transition p-1"
                        title="איפוס סיסמה"
                      >
                        <KeyRound size={15} />
                      </button>
                      {u.id !== currentUser?.id && (
                        <button
                          onClick={() => { if (confirm(`למחוק את ${u.first_name} ${u.last_name}?`)) deleteMutation.mutate(u.id); }}
                          className="text-gray-400 hover:text-red-500 transition p-1"
                          title="מחיקה"
                        >
                          <Trash2 size={15} />
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Invite modal */}
      {showInvite && <InviteModal onClose={() => setShowInvite(false)} onSuccess={() => { setShowInvite(false); qc.invalidateQueries({ queryKey: ["users"] }); }} />}

      {/* Reset password modal */}
      {resetUserId !== null && (
        <ResetPasswordModal
          userId={resetUserId}
          userName={users.find((u) => u.id === resetUserId)?.first_name || ""}
          onClose={() => setResetUserId(null)}
        />
      )}
    </div>
  );
}

function InviteModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [role, setRole] = useState("appraiser");
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!email || !firstName || !lastName || !password) {
      setError("יש למלא את כל השדות");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await api.post("/users", { email, first_name: firstName, last_name: lastName, role, password });
      onSuccess();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "שגיאה ביצירת משתמש");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-gray-900">הוספת משתמש חדש</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">שם פרטי</label>
              <input value={firstName} onChange={(e) => setFirstName(e.target.value)} className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">שם משפחה</label>
              <input value={lastName} onChange={(e) => setLastName(e.target.value)} className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 text-sm" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">אימייל</label>
            <input type="email" dir="ltr" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 text-sm" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">סיסמה ראשונית</label>
            <input type="text" dir="ltr" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="לפחות 6 תווים" className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 text-sm" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">תפקיד</label>
            <select value={role} onChange={(e) => setRole(e.target.value)} className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 text-sm">
              <option value="admin">מנהל — גישה מלאה</option>
              <option value="appraiser">שמאי — עריכה והפקת דוחות</option>
              <option value="viewer">צפייה בלבד — קריאה בלבד</option>
            </select>
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <button onClick={handleSubmit} disabled={saving} className="w-full py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition disabled:opacity-50">
            {saving ? "שומר..." : "צור משתמש"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ResetPasswordModal({ userId, userName, onClose }: { userId: number; userName: string; onClose: () => void }) {
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const handleSubmit = async () => {
    if (password.length < 6) { setError("הסיסמה חייבת להכיל לפחות 6 תווים"); return; }
    setSaving(true);
    setError("");
    try {
      await api.post(`/users/${userId}/reset-password`, { new_password: password });
      setDone(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "שגיאה באיפוס סיסמה");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-sm p-6" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-gray-900 mb-4">איפוס סיסמה — {userName}</h3>
        {done ? (
          <div className="text-center py-4">
            <p className="text-green-600 font-medium">הסיסמה אופסה בהצלחה</p>
            <button onClick={onClose} className="mt-4 px-6 py-2 bg-gray-100 rounded-xl text-sm">סגור</button>
          </div>
        ) : (
          <div className="space-y-4">
            <input type="text" dir="ltr" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="סיסמה חדשה (6+ תווים)" className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 text-sm" />
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <button onClick={handleSubmit} disabled={saving} className="w-full py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition disabled:opacity-50">
              {saving ? "..." : "אפס סיסמה"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
