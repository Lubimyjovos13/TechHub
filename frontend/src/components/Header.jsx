import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/context/AuthContext";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { GraduationCap, Plus, UserCircle, SignOut, Shield, Translate, Palette } from "@phosphor-icons/react";
import i18n from "@/i18n";

export const Header = () => {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const toggleLang = () => {
    const next = i18n.language === "ru" ? "en" : "ru";
    i18n.changeLanguage(next);
    localStorage.setItem("th_lang", next);
  };

  return (
    <header className="sticky top-0 z-50 bg-white border-b-2 border-slate-900">
      <div className="max-w-[1500px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2 shrink-0" data-testid="logo-link">
          <div className="w-10 h-10 bg-sky-200 border-2 border-slate-900 rounded-lg flex items-center justify-center nb-shadow-sm">
            <GraduationCap size={22} weight="bold" className="text-slate-900" />
          </div>
          <span className="font-heading font-extrabold text-xl tracking-tight hidden sm:block">TeachHub</span>
        </Link>

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            onClick={toggleLang}
            data-testid="lang-toggle"
            className="flex items-center gap-1.5 px-3 py-2 bg-violet-200 border-2 border-slate-900 rounded-md font-bold text-sm nb-shadow-sm nb-press"
            aria-label="Toggle language"
          >
            <Translate size={16} weight="bold" />
            {i18n.language === "ru" ? "RU" : "EN"}
          </button>

          {user ? (
            <>
              <Link
                to="/publish"
                data-testid="header-publish-btn"
                className="flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-yellow-300 border-2 border-slate-900 rounded-md font-bold text-sm nb-shadow-sm nb-press"
              >
                <Plus size={16} weight="bold" />
                <span className="hidden sm:inline">{t("nav.publish")}</span>
              </Link>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button data-testid="profile-menu-trigger" className="flex items-center gap-2 px-2 py-1.5 bg-white border-2 border-slate-900 rounded-md nb-shadow-sm nb-press" aria-label="Profile menu">
                    <UserCircle size={22} weight="bold" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="border-2 border-slate-900 nb-shadow">
                  <div className="px-2 py-1.5 text-sm font-bold truncate max-w-[200px]">{user.name}</div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => navigate("/profile")} data-testid="menu-profile" className="font-semibold cursor-pointer">
                    <UserCircle size={16} className="mr-2" /> {t("nav.profile")}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => navigate("/workspace")} data-testid="menu-workspace" className="font-semibold cursor-pointer">
                    <Palette size={16} className="mr-2" /> {t("nav.workspace")}
                  </DropdownMenuItem>
                  {user.role === "admin" && (
                    <DropdownMenuItem onClick={() => navigate("/admin")} data-testid="menu-admin" className="font-semibold cursor-pointer">
                      <Shield size={16} className="mr-2" /> {t("nav.admin")}
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => { logout(); navigate("/"); }} data-testid="menu-logout" className="font-semibold cursor-pointer text-red-600">
                    <SignOut size={16} className="mr-2" /> {t("nav.logout")}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          ) : (
            <>
              <Link to="/login" data-testid="header-login-btn" className="px-3 sm:px-4 py-2 bg-white border-2 border-slate-900 rounded-md font-bold text-sm nb-shadow-sm nb-press">
                {t("nav.login")}
              </Link>
              <Link to="/register" data-testid="header-register-btn" className="px-3 sm:px-4 py-2 bg-yellow-300 border-2 border-slate-900 rounded-md font-bold text-sm nb-shadow-sm nb-press hidden sm:block">
                {t("nav.register")}
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
