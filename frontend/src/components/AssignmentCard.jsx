import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { FILE_URL } from "@/lib/api";
import { Eye, Heart, Calculator, Atom, Flask, BookOpen, Scroll, Globe, PuzzlePiece, PlayCircle, FileArrowDown, Article } from "@phosphor-icons/react";

const SUBJECT_STYLE = {
  mathematics: { bg: "bg-sky-200", Icon: Calculator },
  physics: { bg: "bg-violet-200", Icon: Atom },
  chemistry: { bg: "bg-emerald-200", Icon: Flask },
  literature: { bg: "bg-rose-200", Icon: BookOpen },
  history: { bg: "bg-amber-200", Icon: Scroll },
  foreign_languages: { bg: "bg-orange-200", Icon: Globe },
  other: { bg: "bg-slate-200", Icon: PuzzlePiece },
};

const TYPE_META = {
  html: { Icon: PlayCircle, bg: "bg-sky-300" },
  worksheet: { Icon: FileArrowDown, bg: "bg-emerald-300" },
  blog: { Icon: Article, bg: "bg-yellow-300" },
};

export const AssignmentCard = ({ task }) => {
  const { t } = useTranslation();
  const style = SUBJECT_STYLE[task.subject] || SUBJECT_STYLE.other;
  const Icon = style.Icon;
  const type = task.type || "html";
  const typeMeta = TYPE_META[type] || TYPE_META.html;
  const TypeIcon = typeMeta.Icon;
  const coverImage = (task.files || []).find((f) => f.is_image || (f.content_type || "").startsWith("image/"));

  return (
    <Link
      to={`/assignment/${task.id}`}
      data-testid={`assignment-card-${task.id}`}
      className="nb-card nb-press flex flex-col overflow-hidden group"
    >
      <div className={`${style.bg} border-b-2 border-slate-900 h-32 flex items-center justify-center relative overflow-hidden`}>
        {coverImage ? (
          <img src={FILE_URL(coverImage.file_id)} alt="" className="absolute inset-0 w-full h-full object-cover" />
        ) : (
          <Icon size={52} weight="duotone" className="text-slate-900" />
        )}
        <span className="absolute top-2 left-2 flex items-center gap-1 text-xs font-bold bg-white border-2 border-slate-900 rounded-full px-2 py-0.5 z-10" data-testid={`card-type-${task.id}`}>
          <TypeIcon size={13} weight="bold" /> {t(`types.${type}`)}
        </span>
        <span className="absolute top-2 right-2 text-xs font-bold bg-white border-2 border-slate-900 rounded-full px-2 py-0.5 z-10">
          {t(`grades.${task.grade}`)}
        </span>
      </div>
      <div className="p-4 flex flex-col flex-1">
        <span className="inline-block w-fit text-xs font-bold bg-white border border-slate-900 rounded-full px-2 py-0.5 mb-2">
          {t(`subjects.${task.subject}`)}
        </span>
        <h3 className="font-heading font-bold text-lg leading-tight tracking-tight line-clamp-2 mb-1">
          {task.title}
        </h3>
        {task.description && (
          <p className="text-sm text-slate-600 line-clamp-2 mb-3">{task.description}</p>
        )}
        <div className="mt-auto flex items-center justify-between pt-2 text-sm">
          <span className="text-slate-500 font-medium truncate max-w-[55%]">{t("card.by")} {task.author_name}</span>
          <div className="flex items-center gap-3 text-slate-700 font-semibold">
            <span className="flex items-center gap-1"><Eye size={16} weight="bold" />{task.views}</span>
            <span className="flex items-center gap-1"><Heart size={16} weight="bold" />{task.likes_count}</span>
          </div>
        </div>
      </div>
    </Link>
  );
};
