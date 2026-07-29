import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PostContent } from "@/components/PostContent";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  GraduationCap, Eye, EyeSlash, UserCircle, FolderSimple, FolderSimplePlus, Plus, PencilSimple,
  PlayCircle, FileArrowDown, Article, Stack, Trash, ArrowsOut, ArrowsIn,
} from "@phosphor-icons/react";

const SUBJECTS = ["mathematics", "physics", "chemistry", "literature", "history", "foreign_languages", "other"];
const TYPE_ICON = { html: PlayCircle, worksheet: FileArrowDown, blog: Article };

export default function Workspace() {
  const { t } = useTranslation();
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();

  const [tasks, setTasks] = useState([]);
  const [folders, setFolders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedKey, setSelectedKey] = useState("all");
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [folderDialog, setFolderDialog] = useState(false);
  const [folderName, setFolderName] = useState("");

  useEffect(() => { if (!authLoading && !user) navigate("/login"); }, [user, authLoading, navigate]);

  const load = () => {
    Promise.all([api.get("/users/me/tasks"), api.get("/folders")])
      .then(([a, b]) => { setTasks(a.data); setFolders(b.data); })
      .catch(() => toast.error(t("common.error")))
      .finally(() => setLoading(false));
  };
  useEffect(() => { if (user) load(); }, [user]);

  const subjectsPresent = useMemo(() => SUBJECTS.filter((s) => tasks.some((x) => x.subject === s)), [tasks]);

  const filteredTasks = useMemo(() => {
    if (selectedKey === "all") return tasks;
    const [kind, val] = selectedKey.split(":");
    if (kind === "type") return tasks.filter((x) => (x.type || "html") === val);
    if (kind === "subject") return tasks.filter((x) => x.subject === val);
    if (kind === "folder") return tasks.filter((x) => x.folder_id === val);
    return tasks;
  }, [tasks, selectedKey]);

  const selectTask = async (id) => {
    setSelectedTaskId(id);
    setPreviewLoading(true);
    try { const res = await api.get(`/tasks/${id}`); setPreview(res.data); }
    catch { toast.error(t("common.error")); }
    finally { setPreviewLoading(false); }
  };

  const createFolder = async () => {
    try {
      const res = await api.post("/folders", { name: folderName });
      setFolders((f) => [...f, res.data]);
      setFolderDialog(false); setFolderName("");
      toast.success(t("workspace.create"));
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  const deleteFolder = async (id, e) => {
    e.stopPropagation();
    try { await api.delete(`/folders/${id}`); setFolders((f) => f.filter((x) => x.id !== id)); if (selectedKey === `folder:${id}`) setSelectedKey("all"); load(); }
    catch (err) { toast.error(formatApiErrorDetail(err.response?.data?.detail)); }
  };

  if (!user) return null;

  const FolderBtn = ({ id, icon: Icon, label, count, deletable }) => (
    <button onClick={() => setSelectedKey(id)} data-testid={`ws-folder-${id}`}
      className={`w-full flex items-center gap-2 px-3 py-2 border-2 border-slate-900 rounded-md font-semibold text-sm nb-press ${selectedKey === id ? "bg-sky-200 nb-shadow-sm" : "bg-white"}`}>
      <Icon size={18} weight="bold" className="shrink-0" />
      <span className="flex-1 text-left truncate">{label}</span>
      {typeof count === "number" && <span className="text-xs bg-white border border-slate-900 rounded-full px-1.5">{count}</span>}
      {deletable && <span onClick={(e) => deleteFolder(id.split(":")[1], e)} className="text-red-600 hover:text-red-800" data-testid={`ws-delete-folder-${id.split(":")[1]}`}><Trash size={14} weight="bold" /></span>}
    </button>
  );

  const PreviewZone = () => (
    <div className="h-full flex flex-col">
      {previewLoading ? (
        <div className="flex-1 flex items-center justify-center font-bold text-slate-500">{t("common.loading")}</div>
      ) : preview ? (
        <div className="flex-1 overflow-auto">
          <div className="flex items-center justify-between mb-3 gap-2">
            <h3 className="font-heading font-bold text-lg truncate">{preview.title}</h3>
            <button onClick={() => navigate(`/assignment/${preview.id}`)} className="text-sm font-bold underline shrink-0" data-testid="ws-open-post">{t("card.open")}</button>
          </div>
          <PostContent task={preview} iframeHeight={fullscreen ? "h-[calc(100vh-160px)]" : "h-[calc(100vh-340px)]"} />
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-slate-400 font-semibold">{t("workspace.selectPost")}</div>
      )}
    </div>
  );

  // ---- Fullscreen mode: only preview zone ----
  if (fullscreen) {
    return (
      <div className="fixed inset-0 z-50 bg-slate-50 p-4 sm:p-6" data-testid="ws-fullscreen">
        <button onClick={() => setFullscreen(false)} data-testid="ws-eye-toggle"
          className="fixed top-4 right-4 z-10 flex items-center gap-2 px-4 py-2.5 bg-slate-900 text-white border-2 border-slate-900 rounded-md font-bold nb-press">
          <ArrowsIn size={18} weight="bold" /> {t("workspace.exit")}
        </button>
        <div className="h-full pt-2">
          <PreviewZone />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-slate-50">
      {/* Zone 1: top bar */}
      <div className="bg-white border-b-2 border-slate-900 px-4 sm:px-6 h-14 flex items-center justify-between" data-testid="ws-zone1">
        <button onClick={() => navigate("/")} className="flex items-center gap-2 nb-press" data-testid="ws-logo" title={t("workspace.logoHint")}>
          <div className="w-9 h-9 bg-sky-200 border-2 border-slate-900 rounded-lg flex items-center justify-center"><GraduationCap size={20} weight="bold" /></div>
          <span className="font-heading font-extrabold hidden sm:block">{t("workspace.title")}</span>
        </button>
        <div className="flex items-center gap-3">
          <button onClick={() => setFullscreen(true)} data-testid="ws-eye-toggle"
            className="flex items-center gap-2 px-3 py-2 bg-yellow-300 border-2 border-slate-900 rounded-md font-bold text-sm nb-shadow-sm nb-press" title={t("workspace.fullscreen")}>
            <Eye size={18} weight="bold" /> <span className="hidden sm:inline">{t("workspace.fullscreen")}</span>
          </button>
          <button onClick={() => navigate("/profile")} data-testid="ws-account" className="w-10 h-10 bg-white border-2 border-slate-900 rounded-md flex items-center justify-center nb-shadow-sm nb-press" title={t("workspace.account")}>
            <UserCircle size={22} weight="bold" />
          </button>
        </div>
      </div>

      {/* Zones 2 & 3 */}
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(320px,420px)_1fr] gap-4 p-4 sm:p-6">
        {/* Zone 2: folders (left) + tasks (right) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4" data-testid="ws-zone2">
          {/* Folders */}
          <div className="nb-card p-3 space-y-3 h-fit">
            <div className="flex items-center justify-between">
              <h4 className="font-heading font-bold text-sm">{t("workspace.folders")}</h4>
            </div>
            <FolderBtn id="all" icon={Stack} label={t("workspace.allTasks")} count={tasks.length} />
            <div>
              <p className="text-xs font-bold text-slate-400 uppercase mb-1 px-1">{t("workspace.byType")}</p>
              <div className="space-y-1.5">
                {["html", "worksheet", "blog"].map((tp) => (
                  <FolderBtn key={tp} id={`type:${tp}`} icon={TYPE_ICON[tp]} label={t(`types.${tp}`)} count={tasks.filter((x) => (x.type || "html") === tp).length} />
                ))}
              </div>
            </div>
            {subjectsPresent.length > 0 && (
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase mb-1 px-1">{t("workspace.bySubject")}</p>
                <div className="space-y-1.5">
                  {subjectsPresent.map((s) => (
                    <FolderBtn key={s} id={`subject:${s}`} icon={FolderSimple} label={t(`subjects.${s}`)} count={tasks.filter((x) => x.subject === s).length} />
                  ))}
                </div>
              </div>
            )}
            <div>
              <p className="text-xs font-bold text-slate-400 uppercase mb-1 px-1">{t("workspace.myFolders")}</p>
              <div className="space-y-1.5">
                {folders.map((f) => (
                  <FolderBtn key={f.id} id={`folder:${f.id}`} icon={FolderSimple} label={f.name} count={f.count} deletable />
                ))}
              </div>
              <button onClick={() => setFolderDialog(true)} data-testid="ws-create-folder"
                className="w-full mt-2 flex items-center justify-center gap-1 px-3 py-2 bg-emerald-200 border-2 border-slate-900 rounded-md font-bold text-sm nb-shadow-sm nb-press">
                <FolderSimplePlus size={16} weight="bold" /> {t("workspace.createFolder")}
              </button>
            </div>
          </div>

          {/* Tasks list */}
          <div className="nb-card p-3 h-fit" data-testid="ws-tasks">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-heading font-bold text-sm">{t("workspace.posts")}</h4>
              <button onClick={() => navigate("/publish")} data-testid="ws-new-post" className="flex items-center gap-1 px-2 py-1 bg-yellow-300 border-2 border-slate-900 rounded-md font-bold text-xs nb-shadow-sm nb-press">
                <Plus size={14} weight="bold" /> {t("workspace.newPost")}
              </button>
            </div>
            {loading ? (
              <p className="text-sm font-bold text-slate-500 p-4">{t("common.loading")}</p>
            ) : filteredTasks.length === 0 ? (
              <p className="text-sm font-semibold text-slate-400 p-4 text-center">{t("workspace.noPosts")}</p>
            ) : (
              <div className="space-y-2 max-h-[calc(100vh-260px)] overflow-auto pr-1">
                {filteredTasks.map((tk) => {
                  const Icon = TYPE_ICON[tk.type || "html"];
                  return (
                    <div key={tk.id} onClick={() => selectTask(tk.id)} data-testid={`ws-task-${tk.id}`}
                      className={`flex items-center gap-2 p-2 border-2 border-slate-900 rounded-md cursor-pointer nb-press ${selectedTaskId === tk.id ? "bg-sky-200 nb-shadow-sm" : "bg-white"}`}>
                      <Icon size={18} weight="bold" className="shrink-0" />
                      <span className="flex-1 text-sm font-semibold truncate">{tk.title}</span>
                      <button onClick={(e) => { e.stopPropagation(); navigate(`/edit/${tk.id}`); }} data-testid={`ws-edit-${tk.id}`}
                        className="p-1 text-slate-700 hover:text-slate-900" title={t("workspace.edit")}>
                        <PencilSimple size={16} weight="bold" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Zone 3: preview */}
        <div className="nb-card p-4 min-h-[60vh]" data-testid="ws-zone3">
          <PreviewZone />
        </div>
      </div>

      <Dialog open={folderDialog} onOpenChange={setFolderDialog}>
        <DialogContent className="border-2 border-slate-900 nb-shadow">
          <DialogHeader><DialogTitle className="font-heading">{t("workspace.createFolder")}</DialogTitle></DialogHeader>
          <input value={folderName} onChange={(e) => setFolderName(e.target.value)} placeholder={t("workspace.folderName")} data-testid="ws-folder-name" className="nb-input" />
          <DialogFooter className="gap-2">
            <button onClick={() => setFolderDialog(false)} className="px-4 py-2 bg-white border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press">{t("common.cancel")}</button>
            <button onClick={createFolder} disabled={!folderName.trim()} data-testid="ws-folder-create" className="px-4 py-2 bg-yellow-300 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press disabled:opacity-50">{t("workspace.create")}</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
