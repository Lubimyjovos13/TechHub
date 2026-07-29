import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { formatApiErrorDetail } from "@/lib/api";
import { GraduationCap } from "@phosphor-icons/react";

export default function Register() {
  const { t } = useTranslation();
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await register(email, password, name);
      toast.success(t("auth.registerSuccess"));
      navigate("/");
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md nb-card p-8 nb-rise">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-11 h-11 bg-emerald-200 border-2 border-slate-900 rounded-lg flex items-center justify-center">
            <GraduationCap size={24} weight="bold" />
          </div>
          <h1 className="font-heading text-2xl font-extrabold tracking-tight">{t("auth.registerTitle")}</h1>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block font-bold text-sm mb-1">{t("auth.name")}</label>
            <input required value={name} onChange={(e) => setName(e.target.value)} data-testid="register-name" className="nb-input" />
          </div>
          <div>
            <label className="block font-bold text-sm mb-1">{t("auth.email")}</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="register-email" className="nb-input" />
          </div>
          <div>
            <label className="block font-bold text-sm mb-1">{t("auth.password")}</label>
            <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} data-testid="register-password" className="nb-input" />
            <p className="text-xs text-slate-500 mt-1">{t("auth.passwordHint")}</p>
          </div>
          {error && <p className="text-red-600 font-semibold text-sm" data-testid="register-error">{error}</p>}
          <button type="submit" disabled={loading} data-testid="register-submit" className="w-full py-3 bg-yellow-300 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press disabled:opacity-60">
            {loading ? t("common.loading") : t("auth.registerBtn")}
          </button>
        </form>
        <p className="text-sm text-center mt-5 text-slate-600">
          {t("auth.haveAccount")}{" "}
          <Link to="/login" className="font-bold text-slate-900 underline" data-testid="go-login">{t("nav.login")}</Link>
        </p>
      </div>
    </div>
  );
}
