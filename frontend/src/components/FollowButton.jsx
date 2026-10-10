import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import api, { formatApiErrorDetail, FILE_URL } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { UserCircle, UserPlus, Check } from "@phosphor-icons/react";

export const FollowButton = ({ userId, initialFollowing, onChange, size = "md" }) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [following, setFollowing] = useState(initialFollowing);
  const [busy, setBusy] = useState(false);

  if (!user || user.id === userId) return null;

  const toggle = async () => {
    setBusy(true);
    try {
      const res = await api.post(`/users/${userId}/follow`);
      setFollowing(res.data.following);
      onChange?.(res.data);
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const pad = size === "sm" ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm";
  return (
    <button onClick={toggle} disabled={busy} data-testid={`follow-btn-${userId}`}
      className={`flex items-center gap-1.5 ${pad} border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press ${following ? "bg-white" : "bg-yellow-300"}`}>
      {following ? <Check size={15} weight="bold" /> : <UserPlus size={15} weight="bold" />}
      {following ? t("follow.following") : t("follow.follow")}
    </button>
  );
};

export const UserListItem = ({ u }) => (
  <div className="flex items-center gap-3 p-3 border-2 border-slate-900 rounded-md bg-white" data-testid={`user-item-${u.id}`}>
    <div className="w-10 h-10 bg-sky-200 border-2 border-slate-900 rounded-md flex items-center justify-center shrink-0 overflow-hidden">
      {u.avatar_file_id ? <img src={FILE_URL(u.avatar_file_id)} alt="" className="w-full h-full object-cover" /> : <UserCircle size={22} weight="bold" />}
    </div>
    <Link to={`/u/${u.id}`} className="flex-1 font-bold truncate hover:underline">{u.name}</Link>
    <FollowButton userId={u.id} initialFollowing={u.is_following} size="sm" />
  </div>
);
