import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PostContent } from "@/components/PostContent";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import { Heart, Star, Flag, PencilSimple, Trash, Eye, CaretLeft, UserCircle, PlayCircle, FileArrowDown, Article } from "@phosphor-icons/react";

const TYPE_ICON = { html: PlayCircle, worksheet: FileArrowDown, blog: Article };

export default function AssignmentView() {
  const { t } = useTranslation();
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reportOpen, setReportOpen] = useState(false);
  const [reportReason, setReportReason] = useState("");
  const [delOpen, setDelOpen] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.get(`/tasks/${id}`).then((res) => setTask(res.data)).catch(() => setError(t("common.error"))).finally(() => setLoading(false));
  }, [id, t]);

  const requireLogin = () => { if (!user) { toast.error(t("view.loginToInteract")); navigate("/login"); return true; } return false; };

  const toggleLike = async () => {
    if (requireLogin()) return;
    const res = await api.post(`/tasks/${id}/like`);
    setTask((tk) => ({ ...tk, liked: res.data.liked, likes_count: res.data.likes_count }));
  };
  const toggleFav = async () => {
    if (requireLogin()) return;
    const res = await api.post(`/tasks/${id}/favorite`);
    setTask((tk) => ({ ...tk, favorited: res.data.favorited }));
    toast.success(res.data.favorited ? t("view.favorited") : t("view.favorite"));
  };
  const submitReport = async () => {
    try { await api.post(`/tasks/${id}/report`, { reason: reportReason }); toast.success(t("report.success")); setReportOpen(false); setReportReason(""); }
    catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };
  const doDelete = async () => {
    try { await api.delete(`/tasks/${id}`); toast.success(t("view.delete")); navigate("/"); }
    catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  if (loading) return <div className="max-w-5xl mx-auto px-6 py-20 text-center font-bold" data-testid="view-loading">{t("common.loading")}</div>;
  if (error || !task) return <div className="max-w-5xl mx-auto px-6 py-20 text-center font-bold text-red-600" data-testid="view-error">{error || t("common.error")}</div>;

  const isOwner = user && (user.id === task.author_id || user.role === "admin");
  const TypeIcon = TYPE_ICON[task.type] || PlayCircle;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <Link to="/" className="inline-flex items-center gap-1 font-bold text-sm mb-5 hover:underline" data-testid="back-to-feed">
        <CaretLeft size={16} weight="bold" /> {t("view.back")}
      </Link>

      <div className="nb-card p-6 mb-6 nb-rise">
        <div className="flex flex-wrap gap-2 mb-3">
          <span className="flex items-center gap-1 text-xs font-bold bg-yellow-300 border border-slate-900 rounded-full px-3 py-1"><TypeIcon size={13} weight="bold" /> {t(`types.${task.type}`)}</span>
          <span className="text-xs font-bold bg-sky-200 border border-slate-900 rounded-full px-3 py-1">{t(`subjects.${task.subject}`)}</span>
          <span className="text-xs font-bold bg-violet-200 border border-slate-900 rounded-full px-3 py-1">{t(`grades.${task.grade}`)}</span>
          {task.tags?.map((tag) => <span key={tag} className="text-xs font-bold bg-slate-100 border border-slate-900 rounded-full px-3 py-1">#{tag}</span>)}
        </div>
        <h1 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tight mb-2" data-testid="view-title">{task.title}</h1>
        {task.description && <p className="text-slate-600 mb-3 max-w-3xl">{task.description}</p>}
        <div className="flex flex-wrap items-center gap-4 text-sm font-semibold text-slate-600">
          <Link to={`/u/${task.author_id}`} className="flex items-center gap-1 hover:underline" data-testid="author-link"><UserCircle size={18} weight="bold" /> {task.author_name}</Link>
          <span className="flex items-center gap-1"><Eye size={16} weight="bold" /> {task.views} {t("view.views")}</span>
          <span className="flex items-center gap-1"><Heart size={16} weight="bold" /> {task.likes_count}</span>
        </div>
      </div>

      <div className="mb-6">
        <PostContent task={task} iframeHeight="h-[75vh]" />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button onClick={toggleLike} data-testid="like-btn" className={`flex items-center gap-2 px-4 py-2.5 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press ${task.liked ? "bg-rose-300" : "bg-white"}`}>
          <Heart size={18} weight={task.liked ? "fill" : "bold"} /> {task.liked ? t("view.liked") : t("view.like")} · {task.likes_count}
        </button>
        <button onClick={toggleFav} data-testid="favorite-btn" className={`flex items-center gap-2 px-4 py-2.5 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press ${task.favorited ? "bg-yellow-300" : "bg-white"}`}>
          <Star size={18} weight={task.favorited ? "fill" : "bold"} /> {task.favorited ? t("view.favorited") : t("view.favorite")}
        </button>
        {user && (
          <button onClick={() => setReportOpen(true)} data-testid="report-btn" className="flex items-center gap-2 px-4 py-2.5 bg-white border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press">
            <Flag size={18} weight="bold" /> {t("view.report")}
          </button>
        )}
        {isOwner && (
          <>
            <button onClick={() => navigate(`/edit/${task.id}`)} data-testid="edit-btn" className="flex items-center gap-2 px-4 py-2.5 bg-emerald-200 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press ml-auto">
              <PencilSimple size={18} weight="bold" /> {t("view.edit")}
            </button>
            <button onClick={() => setDelOpen(true)} data-testid="delete-btn" className="flex items-center gap-2 px-4 py-2.5 bg-red-300 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press">
              <Trash size={18} weight="bold" /> {t("view.delete")}
            </button>
          </>
        )}
      </div>

      <Dialog open={reportOpen} onOpenChange={setReportOpen}>
        <DialogContent className="border-2 border-slate-900 nb-shadow">
          <DialogHeader><DialogTitle className="font-heading">{t("report.title")}</DialogTitle>
          <DialogDescription>{t("report.reason")}</DialogDescription></DialogHeader>
          <textarea rows={4} value={reportReason} onChange={(e) => setReportReason(e.target.value)} data-testid="report-reason" className="nb-input resize-none" />
          <DialogFooter>
            <button onClick={submitReport} disabled={!reportReason.trim()} data-testid="report-submit" className="px-5 py-2.5 bg-yellow-300 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press disabled:opacity-50">{t("report.submit")}</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={delOpen} onOpenChange={setDelOpen}>
        <DialogContent className="border-2 border-slate-900 nb-shadow">
          <DialogHeader><DialogTitle className="font-heading">{t("view.delete")}</DialogTitle>
          <DialogDescription>{t("view.deleteConfirm")}</DialogDescription></DialogHeader>
          <DialogFooter className="gap-2">
            <button onClick={() => setDelOpen(false)} className="px-5 py-2.5 bg-white border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press">{t("common.cancel")}</button>
            <button onClick={doDelete} data-testid="confirm-delete" className="px-5 py-2.5 bg-red-400 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press">{t("view.delete")}</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
