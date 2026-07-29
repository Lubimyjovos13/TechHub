import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api from "@/lib/api";
import { AssignmentCard } from "@/components/AssignmentCard";
import { FollowButton, UserListItem } from "@/components/FollowButton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { UserCircle, Shield } from "@phosphor-icons/react";

export default function PublicProfile() {
  const { t } = useTranslation();
  const { id } = useParams();
  const [profile, setProfile] = useState(null);
  const [posts, setPosts] = useState([]);
  const [followers, setFollowers] = useState([]);
  const [following, setFollowing] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true); setError("");
    Promise.all([
      api.get(`/users/${id}`),
      api.get(`/users/${id}/tasks`, { params: { limit: 24 } }),
      api.get(`/users/${id}/followers`),
      api.get(`/users/${id}/following`),
    ]).then(([p, ts, fl, fg]) => {
      setProfile(p.data); setPosts(ts.data.items); setFollowers(fl.data); setFollowing(fg.data);
    }).catch(() => setError(t("common.error"))).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [id, t]);

  if (loading) return <div className="max-w-[1500px] mx-auto px-6 py-20 text-center font-bold">{t("common.loading")}</div>;
  if (error || !profile) return <div className="max-w-[1500px] mx-auto px-6 py-20 text-center font-bold text-red-600">{error || t("common.error")}</div>;

  const Stat = ({ value, label, testId }) => (
    <div className="text-center" data-testid={testId}>
      <div className="font-heading text-2xl font-extrabold">{value}</div>
      <div className="text-xs font-bold text-slate-500 uppercase">{label}</div>
    </div>
  );

  return (
    <div className="max-w-[1500px] mx-auto px-4 sm:px-6 py-8">
      <div className="nb-card p-6 mb-8 nb-rise">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="w-16 h-16 bg-sky-200 border-2 border-slate-900 rounded-lg flex items-center justify-center shrink-0"><UserCircle size={36} weight="bold" /></div>
          <div className="flex-1">
            <h1 className="font-heading text-3xl font-extrabold tracking-tight flex items-center gap-2" data-testid="profile-name">
              {profile.name}
              {profile.role === "admin" && <span className="flex items-center gap-1 text-xs font-bold bg-yellow-300 border border-slate-900 rounded-full px-2 py-0.5"><Shield size={12} weight="bold" /> admin</span>}
            </h1>
          </div>
          <FollowButton userId={profile.id} initialFollowing={profile.is_following} onChange={load} />
        </div>
        <div className="flex gap-8 mt-5">
          <Stat value={profile.post_count} label={t("follow.posts")} testId="stat-posts" />
          <Stat value={profile.followers_count} label={t("follow.followers")} testId="stat-followers" />
          <Stat value={profile.following_count} label={t("follow.followingList")} testId="stat-following" />
        </div>
      </div>

      <Tabs defaultValue="posts">
        <TabsList className="bg-white border-2 border-slate-900 nb-shadow-sm p-1 h-auto flex-wrap">
          <TabsTrigger value="posts" data-testid="pp-tab-posts" className="font-bold data-[state=active]:bg-sky-200 data-[state=active]:border-2 data-[state=active]:border-slate-900">{t("follow.posts")}</TabsTrigger>
          <TabsTrigger value="followers" data-testid="pp-tab-followers" className="font-bold data-[state=active]:bg-yellow-300 data-[state=active]:border-2 data-[state=active]:border-slate-900">{t("follow.followers")}</TabsTrigger>
          <TabsTrigger value="following" data-testid="pp-tab-following" className="font-bold data-[state=active]:bg-violet-200 data-[state=active]:border-2 data-[state=active]:border-slate-900">{t("follow.followingList")}</TabsTrigger>
        </TabsList>

        <TabsContent value="posts" className="mt-6">
          {posts.length === 0 ? <div className="nb-card p-12 text-center font-semibold text-slate-500">{t("follow.noPosts")}</div> : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6" data-testid="pp-posts-grid">
              {posts.map((p) => <AssignmentCard key={p.id} task={p} />)}
            </div>
          )}
        </TabsContent>
        <TabsContent value="followers" className="mt-6">
          {followers.length === 0 ? <div className="nb-card p-12 text-center font-semibold text-slate-500">{t("profile.noFollowers")}</div> : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-w-4xl" data-testid="pp-followers">{followers.map((u) => <UserListItem key={u.id} u={u} />)}</div>
          )}
        </TabsContent>
        <TabsContent value="following" className="mt-6">
          {following.length === 0 ? <div className="nb-card p-12 text-center font-semibold text-slate-500">{t("profile.noFollowing")}</div> : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-w-4xl" data-testid="pp-following">{following.map((u) => <UserListItem key={u.id} u={u} />)}</div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
