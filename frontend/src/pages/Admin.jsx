import { useEffect, useState, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Users, Flag, Stack, Trash, Warning, DownloadSimple, UploadSimple, UserGear } from "@phosphor-icons/react";

const fmtDate = (v) => (v ? new Date(v).toLocaleString() : "—");
const fmtDur = (s = 0) => `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
const ERR_COLORS = { untouched: "bg-red-300", in_progress: "bg-amber-300", fixed: "bg-emerald-300" };

export default function Admin() {
  const { t } = useTranslation();
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [reports, setReports] = useState([]);
  const [errs, setErrs] = useState([]);
  const [loading, setLoading] = useState(true);
  const importRef = useRef(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user) { navigate("/login"); return; }
    if (user.role !== "admin") navigate("/");
  }, [user, authLoading, navigate]);

  const load = () => {
    Promise.all([api.get("/admin/stats"), api.get("/admin/users"), api.get("/admin/reports"), api.get("/admin/error-reports")])
      .then(([s, u, r, e]) => { setStats(s.data); setUsers(u.data); setReports(r.data); setErrs(e.data); })
      .catch(() => toast.error(t("common.error")))
      .finally(() => setLoading(false));
  };
  useEffect(() => { if (user?.role === "admin") load(); }, [user]);

  const promote = async (id) => {
    try { await api.post(`/admin/users/${id}/promote`); toast.success(t("adminx.promoted")); load(); }
    catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };
  const setErrStatus = async (id, status) => {
    try { await api.patch(`/admin/error-reports/${id}`, { status }); setErrs((p) => p.map((x) => x.id === id ? { ...x, status } : x)); }
    catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };
  const download = async (path, filename) => {
    try {
      const res = await api.get(path, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url);
    } catch (e) { toast.error(t("common.error")); }
  };
  const importDb = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    try { await api.post("/admin/import/db", fd); toast.success(t("adminx.imported")); load(); }
    catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
    finally { if (importRef.current) importRef.current.value = ""; }
  };

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

      <div className="nb-card p-4 mb-8 flex flex-wrap items-center gap-3" data-testid="admin-data-tools">
        <span className="font-heading font-extrabold mr-2">{t("adminx.tools")}</span>
        <button onClick={() => download("/admin/export/excel", "teachhub_analytics.xlsx")} data-testid="admin-export-excel" className="px-3 py-2 bg-emerald-200 border-2 border-slate-900 rounded font-bold nb-shadow-sm nb-press inline-flex items-center gap-1"><DownloadSimple size={16} weight="bold" />{t("adminx.exportExcel")}</button>
        <button onClick={() => download("/admin/export/db", "teachhub_db.json")} data-testid="admin-export-db" className="px-3 py-2 bg-sky-200 border-2 border-slate-900 rounded font-bold nb-shadow-sm nb-press inline-flex items-center gap-1"><DownloadSimple size={16} weight="bold" />{t("adminx.exportDb")}</button>
        <button onClick={() => importRef.current?.click()} data-testid="admin-import-db" className="px-3 py-2 bg-yellow-300 border-2 border-slate-900 rounded font-bold nb-shadow-sm nb-press inline-flex items-center gap-1"><UploadSimple size={16} weight="bold" />{t("adminx.importDb")}</button>
        <input ref={importRef} type="file" accept=".json,application/json" onChange={importDb} className="hidden" data-testid="admin-import-input" />
      </div>

      <Tabs defaultValue="reports">
        <TabsList className="bg-white border-2 border-slate-900 nb-shadow-sm p-1 h-auto">
          <TabsTrigger value="reports" data-testid="admin-tab-reports" className="font-bold data-[state=active]:bg-rose-200 data-[state=active]:border-2 data-[state=active]:border-slate-900">{t("admin.reports")}</TabsTrigger>
          <TabsTrigger value="users" data-testid="admin-tab-users" className="font-bold data-[state=active]:bg-sky-200 data-[state=active]:border-2 data-[state=active]:border-slate-900">{t("admin.users")}</TabsTrigger>
          <TabsTrigger value="errors" data-testid="admin-tab-errors" className="font-bold data-[state=active]:bg-amber-200 data-[state=active]:border-2 data-[state=active]:border-slate-900"><Warning size={16} weight="bold" className="mr-1" />{t("adminx.errorsTab")} ({errs.filter((x) => x.status !== "fixed").length})</TabsTrigger>
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
                <th className="text-left p-3 font-bold">{t("adminx.folders")}</th>
                <th className="text-left p-3 font-bold">{t("adminx.drafts")}</th>
                <th className="text-left p-3 font-bold">{t("adminx.published")}</th>
                <th className="text-left p-3 font-bold">{t("adminx.timeSpent")}</th>
                <th className="text-left p-3 font-bold">{t("adminx.registered")}</th>
                <th className="text-left p-3 font-bold">{t("adminx.lastLogin")}</th>
                <th className="text-right p-3 font-bold">{t("admin.actions")}</th>
              </tr></thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t-2 border-slate-900" data-testid={`user-row-${u.id}`}>
                    <td className="p-3 font-semibold">{u.name}</td>
                    <td className="p-3">{u.email}</td>
                    <td className="p-3"><span className={`text-xs font-bold border border-slate-900 rounded-full px-2 py-0.5 ${u.role === "admin" ? "bg-yellow-300" : "bg-sky-200"}`}>{u.role}</span></td>
                    <td className="p-3" data-testid={`user-folders-${u.id}`}>{u.folders_count}</td>
                    <td className="p-3" data-testid={`user-drafts-${u.id}`}>{u.drafts_count}</td>
                    <td className="p-3" data-testid={`user-published-${u.id}`}>{u.published_count}</td>
                    <td className="p-3 whitespace-nowrap">{fmtDur(u.time_spent_seconds)}</td>
                    <td className="p-3 whitespace-nowrap">{fmtDate(u.created_at)}</td>
                    <td className="p-3 whitespace-nowrap">{fmtDate(u.last_login_at)}</td>
                    <td className="p-3 text-right whitespace-nowrap space-x-2">
                      {u.role !== "admin" && <button onClick={() => promote(u.id)} data-testid={`promote-user-${u.id}`} className="px-3 py-1.5 bg-yellow-300 border-2 border-slate-900 rounded font-bold nb-shadow-sm nb-press inline-flex items-center gap-1"><UserGear size={14} weight="bold" />{t("adminx.promote")}</button>}
                      {u.role !== "admin" && <button onClick={() => delUser(u.id)} data-testid={`delete-user-${u.id}`} className="px-3 py-1.5 bg-red-300 border-2 border-slate-900 rounded font-bold nb-shadow-sm nb-press inline-flex items-center gap-1"><Trash size={14} weight="bold" />{t("admin.deleteUser")}</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>

        <TabsContent value="errors" className="mt-6">
          {errs.length === 0 ? (
            <div className="nb-card p-12 text-center font-semibold text-slate-500" data-testid="no-errors">{t("adminx.noErrors")}</div>
          ) : (
            <div className="nb-card overflow-x-auto" data-testid="errors-table">
              <table className="w-full text-sm">
                <thead className="bg-slate-900 text-white"><tr>
                  <th className="text-left p-3 font-bold">{t("adminx.message")}</th>
                  <th className="text-left p-3 font-bold">{t("adminx.page")}</th>
                  <th className="text-left p-3 font-bold">{t("admin.reporter")}</th>
                  <th className="text-left p-3 font-bold">{t("adminx.registered")}</th>
                  <th className="text-right p-3 font-bold">{t("adminx.status")}</th>
                </tr></thead>
                <tbody>
                  {errs.map((r) => (
                    <tr key={r.id} className="border-t-2 border-slate-900" data-testid={`error-row-${r.id}`}>
                      <td className="p-3 max-w-md whitespace-pre-wrap">{r.message}</td>
                      <td className="p-3 max-w-[200px] truncate text-xs">{r.url}</td>
                      <td className="p-3">{r.user_name}</td>
                      <td className="p-3 whitespace-nowrap">{fmtDate(r.created_at)}</td>
                      <td className="p-3 text-right">
                        <select value={r.status} onChange={(e) => setErrStatus(r.id, e.target.value)} data-testid={`error-status-${r.id}`} className={`${ERR_COLORS[r.status]} text-slate-900 border-2 border-slate-900 rounded font-bold px-2 py-1`}>
                          {Object.keys(ERR_COLORS).map((k) => <option key={k} value={k}>{t(`adminx.${k}`)}</option>)}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
