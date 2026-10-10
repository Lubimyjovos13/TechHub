import { useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { PasswordInput } from "@/components/PasswordInput";
import { GraduationCap } from "@phosphor-icons/react";

export default function ResetPassword() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") || "";
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault(); setError("");
    if (pw !== confirm) { setError(t("auth.passwordMismatch")); return; }
    setLoading(true);
    try { await api.post("/auth/reset-password", { token, new_password: pw }); toast.success(t("auth.resetDone")); navigate("/login"); }
    catch (err) { setError(formatApiErrorDetail(err.response?.data?.detail) || err.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md nb-card p-8 nb-rise">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-11 h-11 bg-emerald-200 border-2 border-slate-900 rounded-lg flex items-center justify-center"><GraduationCap size={24} weight="bold" /></div>
          <h1 className="font-heading text-2xl font-extrabold tracking-tight">{t("auth.resetTitle")}</h1>
        </div>
        {!token ? <p className="text-red-600 font-semibold">{t("auth.resetNoToken")}</p> : (
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block font-bold text-sm mb-1">{t("auth.password")}</label>
              <PasswordInput required minLength={8} value={pw} onChange={(e) => setPw(e.target.value)} testId="reset-password" />
            </div>
            <div>
              <label className="block font-bold text-sm mb-1">{t("auth.confirmPassword")}</label>
              <PasswordInput required value={confirm} onChange={(e) => setConfirm(e.target.value)} testId="reset-confirm" />
            </div>
            {error && <p className="text-red-600 font-semibold text-sm" data-testid="reset-error">{error}</p>}
            <button type="submit" disabled={loading} data-testid="reset-submit" className="w-full py-3 bg-yellow-300 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press disabled:opacity-60">
              {loading ? t("common.loading") : t("auth.resetBtn")}
            </button>
          </form>
        )}
        <p className="text-sm text-center mt-5"><Link to="/login" className="font-bold underline">{t("nav.login")}</Link></p>
      </div>
    </div>
  );
}
