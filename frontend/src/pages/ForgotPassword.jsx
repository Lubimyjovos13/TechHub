import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api, { formatApiErrorDetail } from "@/lib/api";
import { GraduationCap } from "@phosphor-icons/react";

export default function ForgotPassword() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault(); setLoading(true); setError("");
    try { await api.post("/auth/forgot-password", { email }); setSent(true); }
    catch (err) { setError(formatApiErrorDetail(err.response?.data?.detail) || err.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md nb-card p-8 nb-rise">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-11 h-11 bg-sky-200 border-2 border-slate-900 rounded-lg flex items-center justify-center"><GraduationCap size={24} weight="bold" /></div>
          <h1 className="font-heading text-2xl font-extrabold tracking-tight">{t("auth.forgotTitle")}</h1>
        </div>
        {sent ? (
          <p className="font-semibold text-emerald-700" data-testid="forgot-sent">{t("auth.forgotSent")}</p>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block font-bold text-sm mb-1">{t("auth.email")}</label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="forgot-email" className="nb-input" />
            </div>
            {error && <p className="text-red-600 font-semibold text-sm">{error}</p>}
            <button type="submit" disabled={loading} data-testid="forgot-submit" className="w-full py-3 bg-yellow-300 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press disabled:opacity-60">
              {loading ? t("common.loading") : t("auth.sendReset")}
            </button>
          </form>
        )}
        <p className="text-sm text-center mt-5"><Link to="/login" className="font-bold underline">{t("nav.login")}</Link></p>
      </div>
    </div>
  );
}
