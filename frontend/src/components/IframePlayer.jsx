import { useTranslation } from "react-i18next";
import { ArrowsOut } from "@phosphor-icons/react";

export const IframePlayer = ({ html, testId = "iframe-player", height = "h-[70vh]" }) => {
  const { t } = useTranslation();

  const openFullscreen = () => {
    const w = window.open("", "_blank");
    if (w) { w.document.open(); w.document.write(html || ""); w.document.close(); }
  };

  return (
    <div className="border-2 border-slate-900 rounded-lg nb-shadow overflow-hidden bg-white">
      <div className="flex items-center justify-between bg-slate-900 px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-400 border border-red-600" />
          <span className="w-3 h-3 rounded-full bg-yellow-300 border border-yellow-500" />
          <span className="w-3 h-3 rounded-full bg-emerald-400 border border-emerald-600" />
          <span className="ml-3 text-xs font-mono text-slate-300">sandbox://player</span>
        </div>
        {html && (
          <button onClick={openFullscreen} data-testid={`${testId}-fullscreen`} className="flex items-center gap-1 text-xs font-bold text-white hover:text-yellow-300" aria-label={t("view.fullscreen")}>
            <ArrowsOut size={14} weight="bold" /> {t("view.fullscreen")}
          </button>
        )}
      </div>
      {html ? (
        <iframe
          title="assignment-player"
          data-testid={testId}
          sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-modals"
          srcDoc={html}
          className={`w-full ${height} bg-white`}
        />
      ) : (
        <div className={`w-full ${height} flex items-center justify-center text-slate-400 font-semibold bg-slate-50`}>
          {t("publish.previewEmpty")}
        </div>
      )}
    </div>
  );
};
