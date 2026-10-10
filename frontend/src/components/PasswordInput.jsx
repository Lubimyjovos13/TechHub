import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Eye, EyeSlash } from "@phosphor-icons/react";

export const PasswordInput = ({ value, onChange, testId, ...props }) => {
  const { t } = useTranslation();
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input
        type={show ? "text" : "password"}
        value={value}
        onChange={onChange}
        data-testid={testId}
        className="nb-input pr-11"
        {...props}
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        data-testid={testId ? `${testId}-toggle` : "password-toggle"}
        aria-label={show ? t("auth.hide") : t("auth.show")}
        className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-600 hover:text-slate-900"
      >
        {show ? <EyeSlash size={20} weight="bold" /> : <Eye size={20} weight="bold" />}
      </button>
    </div>
  );
};
