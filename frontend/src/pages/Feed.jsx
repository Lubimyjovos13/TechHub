import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { AssignmentCard } from "@/components/AssignmentCard";
import { MagnifyingGlass, X, CaretLeft, CaretRight, Compass, UsersThree } from "@phosphor-icons/react";

const SUBJECTS = ["mathematics", "physics", "chemistry", "literature", "history", "foreign_languages", "other"];
const GRADES = ["1-4", "5-6", "7-8", "9-11", "university"];
const TYPES = ["html", "worksheet", "blog"];

export default function Feed() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState({ items: [], total: 0, page: 1, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchInput, setSearchInput] = useState(params.get("search") || "");

  const tab = params.get("tab") === "following" ? "following" : "explore";
  const search = params.get("search") || "";
  const subject = params.get("subject") || "";
  const grade = params.get("grade") || "";
  const type = params.get("type") || "";
  const page = parseInt(params.get("page") || "1", 10);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      if (tab === "following") {
        const res = await api.get("/feed/following", { params: { page, limit: 10 } });
        setData({ ...res.data, pages: res.data.pages || 1 });
      } else {
        const res = await api.get("/tasks", { params: { page, limit: 10, search: search || undefined, subject: subject || undefined, grade: grade || undefined, type: type || undefined } });
        setData(res.data);
      }
    } catch (e) { setError(t("common.error")); }
    finally { setLoading(false); }
  }, [tab, page, search, subject, grade, type, t]);

  useEffect(() => { load(); }, [load]);

  const update = (patch) => {
    const next = new URLSearchParams(params);
    Object.entries(patch).forEach(([k, v]) => { if (v) next.set(k, v); else next.delete(k); });
    if (!("page" in patch)) next.set("page", "1");
    setParams(next);
  };

  const setTab = (tb) => {
    const next = new URLSearchParams();
    if (tb === "following") next.set("tab", "following");
    setParams(next);
  };

  const submitSearch = (e) => { e.preventDefault(); update({ search: searchInput }); };
  const clearAll = () => { setSearchInput(""); setParams(new URLSearchParams()); };
  const hasFilters = search || subject || grade || type;

  const TabBtn = ({ id, Icon, label }) => (
    <button onClick={() => setTab(id)} data-testid={`feed-tab-${id}`}
      className={`flex items-center gap-2 px-4 py-2 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press ${tab === id ? "bg-yellow-300" : "bg-white"}`}>
      <Icon size={18} weight="bold" /> {label}
    </button>
  );

  return (
    <div className="max-w-[1500px] mx-auto px-4 sm:px-6 py-8">
      <div className="mb-6 nb-rise">
        <h1 className="font-heading text-4xl sm:text-5xl font-extrabold tracking-tight mb-2">{t("feed.title")}</h1>
        <p className="text-slate-600 text-base sm:text-lg max-w-2xl">{t("feed.subtitle")}</p>
      </div>

      <div className="flex gap-3 mb-6">
        <TabBtn id="explore" Icon={Compass} label={t("feed.exploreTab")} />
        {user && <TabBtn id="following" Icon={UsersThree} label={t("feed.followingTab")} />}
      </div>

      {tab === "explore" && (
        <div className="nb-card p-4 mb-8">
          <form onSubmit={submitSearch} className="flex flex-col md:flex-row gap-3 flex-wrap">
            <div className="flex-1 min-w-[200px] flex items-center gap-2 border-2 border-slate-900 rounded-md px-3 bg-white focus-within:ring-2 focus-within:ring-sky-300">
              <MagnifyingGlass size={20} weight="bold" className="text-slate-500" />
              <input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder={t("search.placeholder")} data-testid="search-input" className="flex-1 py-2 outline-none bg-transparent" />
            </div>
            <select value={type} onChange={(e) => update({ type: e.target.value })} data-testid="type-filter" className="nb-input md:w-44 font-semibold cursor-pointer">
              <option value="">{t("types.all")}</option>
              {TYPES.map((x) => <option key={x} value={x}>{t(`types.${x}`)}</option>)}
            </select>
            <select value={subject} onChange={(e) => update({ subject: e.target.value })} data-testid="subject-filter" className="nb-input md:w-48 font-semibold cursor-pointer">
              <option value="">{`${t("search.subject")}: ${t("search.all")}`}</option>
              {SUBJECTS.map((s) => <option key={s} value={s}>{t(`subjects.${s}`)}</option>)}
            </select>
            <select value={grade} onChange={(e) => update({ grade: e.target.value })} data-testid="grade-filter" className="nb-input md:w-44 font-semibold cursor-pointer">
              <option value="">{`${t("search.grade")}: ${t("search.all")}`}</option>
              {GRADES.map((g) => <option key={g} value={g}>{t(`grades.${g}`)}</option>)}
            </select>
            <button type="submit" data-testid="search-submit" className="px-5 py-2 bg-sky-300 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press">
              <MagnifyingGlass size={18} weight="bold" />
            </button>
          </form>
          {hasFilters && (
            <div className="flex items-center justify-between mt-3">
              <span className="text-sm font-semibold text-slate-600" data-testid="results-count">{data.total} {t("search.results")}</span>
              <button onClick={clearAll} data-testid="clear-filters" className="flex items-center gap-1 text-sm font-bold text-red-600 hover:underline">
                <X size={14} weight="bold" /> {t("search.clear")}
              </button>
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, i) => <div key={i} className="nb-card h-72 animate-pulse bg-slate-100" />)}
        </div>
      ) : error ? (
        <div className="nb-card p-12 text-center font-bold text-red-600" data-testid="feed-error">{error}</div>
      ) : data.items.length === 0 ? (
        <div className="nb-card p-16 text-center" data-testid="feed-empty">
          <p className="font-heading text-2xl font-bold mb-2">{tab === "following" ? t("feed.followingEmpty") : t("feed.empty")}</p>
          {tab === "explore" && <p className="text-slate-500">{t("feed.emptyPublish")}</p>}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6" data-testid="feed-grid">
            {data.items.map((task) => <AssignmentCard key={task.id} task={task} />)}
          </div>
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-4 mt-10">
              <button disabled={page <= 1} onClick={() => update({ page: String(page - 1) })} data-testid="prev-page" className="flex items-center gap-1 px-4 py-2 bg-white border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press disabled:opacity-40 disabled:pointer-events-none">
                <CaretLeft size={16} weight="bold" /> {t("common.prev")}
              </button>
              <span className="font-bold" data-testid="page-indicator">{t("common.page")} {page} {t("common.of")} {data.pages}</span>
              <button disabled={page >= data.pages} onClick={() => update({ page: String(page + 1) })} data-testid="next-page" className="flex items-center gap-1 px-4 py-2 bg-white border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press disabled:opacity-40 disabled:pointer-events-none">
                {t("common.next")} <CaretRight size={16} weight="bold" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
