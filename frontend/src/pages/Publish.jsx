import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { IframePlayer } from "@/components/IframePlayer";
import { FloppyDisk } from "@phosphor-icons/react";

const SUBJECTS = ["mathematics", "physics", "chemistry", "literature", "history", "foreign_languages", "other"];
const GRADES = ["1-4", "5-6", "7-8", "9-11", "university"];

const SAMPLE = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{font-family:sans-serif;text-align:center;padding:40px;background:#F8FAFC}button{font-size:20px;padding:12px 24px;border:2px solid #0F172A;border-radius:8px;background:#FDE047;cursor:pointer}</style></head><body><h1>2 + 2 = ?</h1><button onclick="document.getElementById('r').innerText='Correct! 🎉'">4</button><p id="r"></p></body></html>`;

export default function Publish() {
  const { t } = useTranslation();
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = Boolean(id);

  const [form, setForm] = useState({ title: "", subject: "", grade: "", description: "", tags: "", html_code: isEdit ? "" : SAMPLE });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(isEdit);

  useEffect(() => {
    if (!authLoading && !user) navigate("/login");
  }, [user, authLoading, navigate]);

  useEffect(() => {
    if (!isEdit) return;
    api.get(`/tasks/${id}`).then((res) => {
      const d = res.data;
      setForm({ title: d.title, subject: d.subject, grade: d.grade, description: d.description || "", tags: (d.tags || []).join(", "), html_code: d.html_code });
    }).catch(() => setError(t("common.error"))).finally(() => setFetching(false));
  }, [id, isEdit, t]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    const payload = {
      title: form.title, subject: form.subject, grade: form.grade,
      description: form.description, html_code: form.html_code,
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

  return (
    <div className="max-w-[1500px] mx-auto px-4 sm:px-6 py-8">
      <h1 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tight mb-6">{isEdit ? t("publish.titleEdit") : t("publish.titleNew")}</h1>
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
            <textarea maxLength={500} rows={3} value={form.description} onChange={set("description")} data-testid="publish-description" className="nb-input resize-none" />
            <p className="text-xs text-slate-500 mt-1">{form.description.length}/500 · {t("publish.descHint")}</p>
          </div>
          <div>
            <label className="block font-bold text-sm mb-1">{t("publish.tags")}</label>
            <input value={form.tags} onChange={set("tags")} data-testid="publish-tags" className="nb-input" />
          </div>
          <div>
            <label className="block font-bold text-sm mb-1">{t("publish.html")}</label>
            <textarea required rows={10} value={form.html_code} onChange={set("html_code")} data-testid="publish-html" className="nb-input font-mono text-sm resize-y" spellCheck={false} />
            <p className="text-xs text-slate-500 mt-1">{t("publish.htmlHint")}</p>
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
          <IframePlayer html={form.html_code} testId="publish-preview" height="h-[70vh]" />
        </div>
      </div>
    </div>
  );
}
