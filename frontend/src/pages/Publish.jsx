import { useEffect, useState, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import api, { formatApiErrorDetail, uploadFile, FILE_URL } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PostContent } from "@/components/PostContent";
import { FloppyDisk, PlayCircle, FileArrowDown, Article, UploadSimple, X, Spinner } from "@phosphor-icons/react";

const SUBJECTS = ["mathematics", "physics", "chemistry", "literature", "history", "foreign_languages", "other"];
const GRADES = ["1-4", "5-6", "7-8", "9-11", "university"];

const SAMPLE = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{font-family:sans-serif;text-align:center;padding:40px;background:#F8FAFC}button{font-size:20px;padding:12px 24px;border:2px solid #0F172A;border-radius:8px;background:#FDE047;cursor:pointer}</style></head><body><h1>2 + 2 = ?</h1><button onclick="document.getElementById('r').innerText='Correct! 🎉'">4</button><p id="r"></p></body></html>`;

const TYPES = [
  { key: "html", Icon: PlayCircle, bg: "bg-sky-300" },
  { key: "worksheet", Icon: FileArrowDown, bg: "bg-emerald-300" },
  { key: "blog", Icon: Article, bg: "bg-yellow-300" },
];

export default function Publish() {
  const { t } = useTranslation();
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = Boolean(id);
  const fileRef = useRef(null);

  const [type, setType] = useState("html");
  const [form, setForm] = useState({ title: "", subject: "", grade: "", description: "", tags: "", html_code: SAMPLE, body: "", folder_id: "" });
  const [files, setFiles] = useState([]);
  const [folders, setFolders] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(isEdit);

  useEffect(() => { if (!authLoading && !user) navigate("/login"); }, [user, authLoading, navigate]);

  useEffect(() => {
    api.get("/folders").then((r) => setFolders(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!isEdit) return;
    api.get(`/tasks/${id}`).then((res) => {
      const d = res.data;
      setType(d.type || "html");
      setForm({ title: d.title, subject: d.subject, grade: d.grade, description: d.description || "", tags: (d.tags || []).join(", "), html_code: d.html_code || SAMPLE, body: d.body || "", folder_id: d.folder_id || "" });
      setFiles(d.files || []);
    }).catch(() => setError(t("common.error"))).finally(() => setFetching(false));
  }, [id, isEdit, t]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const onUpload = async (e) => {
    const selected = Array.from(e.target.files || []);
    if (!selected.length) return;
    setUploading(true);
    try {
      for (const file of selected) {
        const res = await uploadFile(file);
        setFiles((prev) => [...prev, res]);
      }
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const removeFile = (fid) => setFiles((prev) => prev.filter((f) => f.file_id !== fid));

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    const payload = {
      type,
      title: form.title, subject: form.subject, grade: form.grade,
      description: form.description,
      html_code: type === "html" ? form.html_code : null,
      body: type === "blog" ? form.body : null,
      files: type === "html" ? [] : files,
      folder_id: form.folder_id || null,
      tags: form.tags.split(",").map((x) => x.trim()).filter(Boolean),
    };
    try {
      let res;
      if (isEdit) { res = await api.put(`/tasks/${id}`, payload); toast.success(t("publish.updated")); }
      else { res = await api.post("/tasks", payload); toast.success(t("publish.success")); }
      navigate(`/assignment/${res.data.id}`);
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally { setLoading(false); }
  };

  if (fetching) return <div className="max-w-[1500px] mx-auto px-6 py-20 text-center font-bold">{t("common.loading")}</div>;

  const previewTask = { type, html_code: form.html_code, body: form.body, files };
  const accept = type === "blog" ? "image/*" : "image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv";

  return (
    <div className="max-w-[1500px] mx-auto px-4 sm:px-6 py-8">
      <h1 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tight mb-6">{isEdit ? t("publish.titleEdit") : t("publish.titleNew")}</h1>

      <div className="mb-6">
        <p className="font-bold text-sm mb-2">{t("publish.chooseType")}</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {TYPES.map(({ key, Icon, bg }) => (
            <button key={key} type="button" onClick={() => setType(key)} data-testid={`type-${key}`}
              className={`text-left p-4 border-2 border-slate-900 rounded-lg nb-press ${type === key ? `${bg} nb-shadow` : "bg-white nb-shadow-sm"}`}>
              <Icon size={26} weight="bold" className="mb-2" />
              <div className="font-heading font-bold">{t(`types.${key}`)}</div>
              <div className="text-xs text-slate-700 mt-1">{t(`publish.type${key.charAt(0).toUpperCase() + key.slice(1)}Desc`)}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <form onSubmit={submit} className="nb-card p-6 space-y-5" data-testid="publish-form">
          <div>
            <label className="block font-bold text-sm mb-1">{t("publish.formTitle")}</label>
            <input required maxLength={140} value={form.title} onChange={set("title")} data-testid="publish-title" className="nb-input" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-bold text-sm mb-1">{t("publish.subject")}</label>
              <select required value={form.subject} onChange={set("subject")} data-testid="publish-subject" className="nb-input font-semibold">
                <option value="">{t("publish.selectSubject")}</option>
                {SUBJECTS.map((s) => <option key={s} value={s}>{t(`subjects.${s}`)}</option>)}
              </select>
            </div>
            <div>
              <label className="block font-bold text-sm mb-1">{t("publish.grade")}</label>
              <select required value={form.grade} onChange={set("grade")} data-testid="publish-grade" className="nb-input font-semibold">
                <option value="">{t("publish.selectGrade")}</option>
                {GRADES.map((g) => <option key={g} value={g}>{t(`grades.${g}`)}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block font-bold text-sm mb-1">{t("publish.description")}</label>
            <textarea maxLength={500} rows={2} value={form.description} onChange={set("description")} data-testid="publish-description" className="nb-input resize-none" />
            <p className="text-xs text-slate-500 mt-1">{form.description.length}/500 · {t("publish.descHint")}</p>
          </div>

          {type === "html" && (
            <div>
              <label className="block font-bold text-sm mb-1">{t("publish.html")}</label>
              <textarea required rows={10} value={form.html_code} onChange={set("html_code")} data-testid="publish-html" className="nb-input font-mono text-sm resize-y" spellCheck={false} />
              <p className="text-xs text-slate-500 mt-1">{t("publish.htmlHint")}</p>
            </div>
          )}

          {type === "blog" && (
            <div>
              <label className="block font-bold text-sm mb-1">{t("publish.blogBody")}</label>
              <textarea required rows={8} value={form.body} onChange={set("body")} data-testid="publish-body" className="nb-input resize-y" />
              <p className="text-xs text-slate-500 mt-1">{t("publish.blogBodyHint")}</p>
            </div>
          )}

          {(type === "worksheet" || type === "blog") && (
            <div>
              <label className="block font-bold text-sm mb-1">{type === "blog" ? t("publish.blogImages") : t("publish.worksheetFiles")}</label>
              <input ref={fileRef} type="file" multiple accept={accept} onChange={onUpload} className="hidden" data-testid="publish-file-input" />
              <button type="button" onClick={() => fileRef.current?.click()} disabled={uploading} data-testid="publish-upload-btn"
                className="flex items-center gap-2 px-4 py-2.5 bg-violet-200 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press disabled:opacity-60">
                {uploading ? <Spinner size={18} weight="bold" className="animate-spin" /> : <UploadSimple size={18} weight="bold" />}
                {uploading ? t("publish.uploading") : (type === "blog" ? t("publish.uploadImage") : t("publish.uploadFile"))}
              </button>
              <p className="text-xs text-slate-500 mt-1">{type === "worksheet" ? t("publish.worksheetHint") : ""}</p>
              {files.length > 0 && (
                <div className="space-y-2 mt-3" data-testid="uploaded-files">
                  {files.map((f) => (
                    <div key={f.file_id} className="flex items-center gap-3 border-2 border-slate-900 rounded-md p-2 bg-white">
                      {(f.is_image || (f.content_type || "").startsWith("image/")) && (
                        <img src={FILE_URL(f.file_id)} alt="" className="w-10 h-10 object-cover rounded border border-slate-900" />
                      )}
                      <span className="flex-1 text-sm font-semibold truncate">{f.original_filename}</span>
                      <button type="button" onClick={() => removeFile(f.file_id)} data-testid={`remove-file-${f.file_id}`} className="p-1 text-red-600 hover:text-red-800"><X size={18} weight="bold" /></button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-bold text-sm mb-1">{t("publish.tags")}</label>
              <input value={form.tags} onChange={set("tags")} data-testid="publish-tags" className="nb-input" />
            </div>
            <div>
              <label className="block font-bold text-sm mb-1">{t("publish.folder")}</label>
              <select value={form.folder_id} onChange={set("folder_id")} data-testid="publish-folder" className="nb-input font-semibold">
                <option value="">{t("publish.noFolder")}</option>
                {folders.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
              </select>
            </div>
          </div>

          {error && <p className="text-red-600 font-semibold text-sm" data-testid="publish-error">{error}</p>}
          <div className="flex gap-3">
            <button type="submit" disabled={loading} data-testid="publish-submit" className="flex-1 flex items-center justify-center gap-2 py-3 bg-yellow-300 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press disabled:opacity-60">
              <FloppyDisk size={18} weight="bold" /> {loading ? t("common.loading") : (isEdit ? t("publish.update") : t("publish.submit"))}
            </button>
            <button type="button" onClick={() => navigate(-1)} data-testid="publish-cancel" className="px-5 py-3 bg-white border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press">
              {t("publish.cancel")}
            </button>
          </div>
        </form>

        <div className="lg:sticky lg:top-24 lg:self-start">
          <h2 className="font-heading font-bold text-lg mb-2">{t("publish.preview")}</h2>
          <PostContent task={previewTask} iframeHeight="h-[70vh]" />
        </div>
      </div>
    </div>
  );
}
