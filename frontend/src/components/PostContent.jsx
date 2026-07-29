import { useTranslation } from "react-i18next";
import { FILE_URL } from "@/lib/api";
import { IframePlayer } from "@/components/IframePlayer";
import { DownloadSimple, FileText, FilePdf, FileDoc, FileXls, FilePpt, Image as ImageIcon } from "@phosphor-icons/react";

const fileIcon = (ct = "") => {
  if (ct.includes("pdf")) return FilePdf;
  if (ct.includes("word") || ct.includes("msword")) return FileDoc;
  if (ct.includes("sheet") || ct.includes("excel")) return FileXls;
  if (ct.includes("presentation") || ct.includes("powerpoint")) return FilePpt;
  if (ct.startsWith("image/")) return ImageIcon;
  return FileText;
};

export const PostContent = ({ task, iframeHeight = "h-[75vh]" }) => {
  const { t } = useTranslation();
  if (!task) return null;

  if (task.type === "worksheet") {
    const images = (task.files || []).filter((f) => f.is_image || (f.content_type || "").startsWith("image/"));
    const docs = (task.files || []).filter((f) => !(f.is_image || (f.content_type || "").startsWith("image/")));
    return (
      <div className="space-y-6" data-testid="worksheet-content">
        {images.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {images.map((f) => (
              <a key={f.file_id} href={FILE_URL(f.file_id, true)} className="nb-card overflow-hidden nb-press block" data-testid={`worksheet-image-${f.file_id}`}>
                <img src={FILE_URL(f.file_id)} alt={f.original_filename} className="w-full h-auto max-h-[60vh] object-contain bg-slate-50 border-b-2 border-slate-900" />
                <div className="p-3 flex items-center justify-between gap-2">
                  <span className="font-semibold text-sm truncate">{f.original_filename}</span>
                  <DownloadSimple size={18} weight="bold" />
                </div>
              </a>
            ))}
          </div>
        )}
        {docs.length > 0 && (
          <div className="space-y-3">
            <h3 className="font-heading font-bold text-lg">{t("view.attachments")}</h3>
            {docs.map((f) => {
              const Icon = fileIcon(f.content_type);
              return (
                <a key={f.file_id} href={FILE_URL(f.file_id, true)} data-testid={`worksheet-doc-${f.file_id}`}
                   className="nb-card nb-press flex items-center gap-4 p-4">
                  <div className="w-11 h-11 bg-rose-200 border-2 border-slate-900 rounded-md flex items-center justify-center shrink-0"><Icon size={22} weight="bold" /></div>
                  <span className="font-semibold flex-1 truncate">{f.original_filename}</span>
                  <span className="flex items-center gap-1 font-bold text-sm px-3 py-1.5 bg-yellow-300 border-2 border-slate-900 rounded-md"><DownloadSimple size={16} weight="bold" /> {t("card.download")}</span>
                </a>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  if (task.type === "blog") {
    const images = (task.files || []).filter((f) => f.is_image || (f.content_type || "").startsWith("image/"));
    return (
      <article className="nb-card p-6 sm:p-8" data-testid="blog-content">
        <div className="prose max-w-none whitespace-pre-wrap text-slate-800 text-base leading-relaxed font-body">{task.body}</div>
        {images.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
            {images.map((f) => (
              <img key={f.file_id} src={FILE_URL(f.file_id)} alt={f.original_filename} className="w-full h-auto rounded-md border-2 border-slate-900" data-testid={`blog-image-${f.file_id}`} />
            ))}
          </div>
        )}
      </article>
    );
  }

  return <IframePlayer html={task.html_code} testId="view-iframe" height={iframeHeight} />;
};
