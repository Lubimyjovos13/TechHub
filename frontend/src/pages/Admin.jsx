import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Users, Flag, Stack, Trash } from "@phosphor-icons/react";

export default function Admin() {
  const { t } = useTranslation();
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) { navigate("/login"); return; }
    if (user.role !== "admin") navigate("/");
  }, [user, authLoading, navigate]);

  const load = () => {
    Promise.all([api.get("/admin/stats"), api.get("/admin/users"), api.get("/admin/reports")])
      .then(([s, u, r]) => { setStats(s.data); setUsers(u.data); setReports(r.data); })
      .catch(() => toast.error(t("common.error")))
      .finally(() => setLoading(false));
  };
  useEffect(() => { if (user?.role === "admin") load(); }, [user]);

  const delUser = async (id) => {
    if (!window.confirm(t("admin.deleteUserConfirm"))) return;
    try { await api.delete(`/admin/users/${id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };
  const delTask = async (id) => {
    try { await api.delete(`/tasks/${id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };
  const dismiss = async (id) => {
    try { await api.delete(`/admin/reports/${id}`); toast.success("Dismissed"); load(); }
    catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  if (!user || user.role !== "admin") return null;

  const statCard = (label, value, Icon, bg) => (
    <div className={`nb-card p-5 flex items-center gap-4`}>
      <div className={`w-12 h-12 ${bg} border-2 border-slate-900 rounded-md flex items-center justify-center`}><Icon size={24} weight="bold" /></div>
      <div><div className="text-2xl font-heading font-extrabold">{value}</div><div className="text-sm font-semibold text-slate-500">{label}</div></div>
    </div>
  );

  return (
    <div className="max-w-[1500px] mx-auto px-4 sm:px-6 py-8">
      <h1 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tight mb-6">{t("admin.title")}</h1>

      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8" data-testid="admin-stats">
          {statCard(t("admin.stats.users"), stats.users, Users, "bg-sky-200")}
          {statCard(t("admin.stats.tasks"), stats.tasks, Stack, "bg-emerald-200")}
          {statCard(t("admin.stats.reports"), stats.reports, Flag, "bg-rose-200")}
        </div>
      )}

      <Tabs defaultValue="reports">
        <TabsList className="bg-white border-2 border-slate-900 nb-shadow-sm p-1 h-auto">
          <TabsTrigger value="reports" data-testid="admin-tab-reports" className="font-bold data-[state=active]:bg-rose-200 data-[state=active]:border-2 data-[state=active]:border-slate-900">{t("admin.reports")}</TabsTrigger>
          <TabsTrigger value="users" data-testid="admin-tab-users" className="font-bold data-[state=active]:bg-sky-200 data-[state=active]:border-2 data-[state=active]:border-slate-900">{t("admin.users")}</TabsTrigger>
        </TabsList>

        <TabsContent value="reports" className="mt-6">
          {loading ? <p className="font-bold">{t("common.loading")}</p> : reports.length === 0 ? (
            <div className="nb-card p-12 text-center font-semibold text-slate-500" data-testid="no-reports">{t("admin.noReports")}</div>
          ) : (
            <div className="nb-card overflow-x-auto" data-testid="reports-table">
              <table className="w-full text-sm">
                <thead className="bg-slate-900 text-white"><tr>
                  <th className="text-left p-3 font-bold">{t("admin.reportedTask")}</th>
                  <th className="text-left p-3 font-bold">{t("admin.reason")}</th>
                  <th className="text-left p-3 font-bold">{t("admin.reporter")}</th>
                  <th className="text-right p-3 font-bold">{t("admin.actions")}</th>
                </tr></thead>
                <tbody>
                  {reports.map((r) => (
                    <tr key={r.id} className="border-t-2 border-slate-900" data-testid={`report-row-${r.id}`}>
                      <td className="p-3 font-semibold">{r.task ? <Link to={`/assignment/${r.task.id}`} className="underline">{r.task.title}</Link> : <span className="text-slate-400 italic">deleted</span>}</td>
                      <td className="p-3 max-w-xs">{r.reason}</td>
                      <td className="p-3">{r.reporter_name}</td>
                      <td className="p-3">
                        <div className="flex gap-2 justify-end">
                          {r.task && <button onClick={() => delTask(r.task.id)} data-testid={`delete-task-${r.id}`} className="px-3 py-1.5 bg-red-300 border-2 border-slate-900 rounded font-bold nb-shadow-sm nb-press flex items-center gap-1"><Trash size={14} weight="bold" />{t("admin.deleteTask")}</button>}
                          <button onClick={() => dismiss(r.id)} data-testid={`dismiss-report-${r.id}`} className="px-3 py-1.5 bg-white border-2 border-slate-900 rounded font-bold nb-shadow-sm nb-press">{t("admin.dismiss")}</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>

        <TabsContent value="users" className="mt-6">
          <div className="nb-card overflow-x-auto" data-testid="users-table">
            <table className="w-full text-sm">
              <thead className="bg-slate-900 text-white"><tr>
                <th className="text-left p-3 font-bold">{t("admin.userName")}</th>
                <th className="text-left p-3 font-bold">{t("admin.userEmail")}</th>
                <th className="text-left p-3 font-bold">{t("admin.userRole")}</th>
                <th className="text-left p-3 font-bold">{t("admin.userTasks")}</th>
                <th className="text-right p-3 font-bold">{t("admin.actions")}</th>
              </tr></thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t-2 border-slate-900" data-testid={`user-row-${u.id}`}>
                    <td className="p-3 font-semibold">{u.name}</td>
                    <td className="p-3">{u.email}</td>
                    <td className="p-3"><span className={`text-xs font-bold border border-slate-900 rounded-full px-2 py-0.5 ${u.role === "admin" ? "bg-yellow-300" : "bg-sky-200"}`}>{u.role}</span></td>
                    <td className="p-3">{u.task_count}</td>
                    <td className="p-3 text-right">
                      {u.role !== "admin" && <button onClick={() => delUser(u.id)} data-testid={`delete-user-${u.id}`} className="px-3 py-1.5 bg-red-300 border-2 border-slate-900 rounded font-bold nb-shadow-sm nb-press inline-flex items-center gap-1"><Trash size={14} weight="bold" />{t("admin.deleteUser")}</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
