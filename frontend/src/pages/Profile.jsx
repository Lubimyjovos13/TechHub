import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { AssignmentCard } from "@/components/AssignmentCard";
import { UserListItem } from "@/components/FollowButton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { PasswordInput } from "@/components/PasswordInput";
import { Switch } from "@/components/ui/switch";
import { Palette, ArrowSquareOut } from "@phosphor-icons/react";

export default function Profile() {
  const { t } = useTranslation();
  const { user, setUser, logout, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [myTasks, setMyTasks] = useState([]);
  const [favs, setFavs] = useState([]);
  const [followers, setFollowers] = useState([]);
  const [following, setFollowing] = useState([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [curPw, setCurPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [hideFollows, setHideFollows] = useState(false);
  const [delOpen, setDelOpen] = useState(false);

  useEffect(() => { if (authLoading) return; if (!user) { navigate("/login"); return; } setName(user.name); setEmail(user.email); setHideFollows(!!user.hide_follows); }, [user, authLoading, navigate]);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      api.get("/users/me/tasks"), api.get("/users/me/favorites"),
      api.get(`/users/${user.id}/followers`), api.get(`/users/${user.id}/following`),
    ]).then(([a, b, c, d]) => { setMyTasks(a.data); setFavs(b.data); setFollowers(c.data); setFollowing(d.data); })
      .finally(() => setLoading(false));
  }, [user]);

  const saveAccount = async () => {
    try { const res = await api.put("/users/me", { name, email, hide_follows: hideFollows }); setUser(res.data); toast.success(t("profile.saved")); }
    catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };
  const changePw = async () => {
    try { await api.put("/users/me/password", { current_password: curPw, new_password: newPw }); toast.success(t("profile.passwordChanged")); setCurPw(""); setNewPw(""); }
    catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };
  const deleteAcc = async () => {
    try { await api.delete("/users/me"); toast.success(t("profile.accountDeleted")); logout(); navigate("/"); }
    catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  if (!user) return null;

  return (
    <div className="max-w-[1500px] mx-auto px-4 sm:px-6 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <h1 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tight">{t("profile.title")}</h1>
        <div className="flex gap-3">
          <button onClick={() => navigate("/workspace")} data-testid="open-studio" className="flex items-center gap-2 px-4 py-2 bg-sky-300 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press">
            <Palette size={18} weight="bold" /> {t("profile.openStudio")}
          </button>
          <Link to={`/u/${user.id}`} data-testid="view-public-profile" className="flex items-center gap-2 px-4 py-2 bg-white border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press">
            <ArrowSquareOut size={18} weight="bold" /> {t("profile.viewProfile")}
          </Link>
        </div>
      </div>

      <Tabs defaultValue="tasks">
        <TabsList className="bg-white border-2 border-slate-900 nb-shadow-sm p-1 h-auto flex-wrap">
          <TabsTrigger value="tasks" data-testid="tab-tasks" className="font-bold data-[state=active]:bg-sky-200 data-[state=active]:border-2 data-[state=active]:border-slate-900">{t("profile.myTasks")}</TabsTrigger>
          <TabsTrigger value="favs" data-testid="tab-favorites" className="font-bold data-[state=active]:bg-yellow-300 data-[state=active]:border-2 data-[state=active]:border-slate-900">{t("profile.favorites")}</TabsTrigger>
          <TabsTrigger value="followers" data-testid="tab-followers" className="font-bold data-[state=active]:bg-rose-200 data-[state=active]:border-2 data-[state=active]:border-slate-900">{t("profile.followers")}</TabsTrigger>
          <TabsTrigger value="following" data-testid="tab-following" className="font-bold data-[state=active]:bg-emerald-200 data-[state=active]:border-2 data-[state=active]:border-slate-900">{t("profile.following")}</TabsTrigger>
          <TabsTrigger value="settings" data-testid="tab-settings" className="font-bold data-[state=active]:bg-violet-200 data-[state=active]:border-2 data-[state=active]:border-slate-900">{t("profile.settings")}</TabsTrigger>
        </TabsList>

        <TabsContent value="tasks" className="mt-6">
          {loading ? <p className="font-bold">{t("common.loading")}</p> : myTasks.length === 0 ? (
            <div className="nb-card p-12 text-center font-semibold text-slate-500" data-testid="no-tasks">{t("profile.noTasks")}</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6" data-testid="my-tasks-grid">
              {myTasks.map((tk) => <AssignmentCard key={tk.id} task={tk} />)}
            </div>
          )}
        </TabsContent>

        <TabsContent value="favs" className="mt-6">
          {loading ? <p className="font-bold">{t("common.loading")}</p> : favs.length === 0 ? (
            <div className="nb-card p-12 text-center font-semibold text-slate-500" data-testid="no-favorites">{t("profile.noFavorites")}</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6" data-testid="favorites-grid">
              {favs.map((tk) => <AssignmentCard key={tk.id} task={tk} />)}
            </div>
          )}
        </TabsContent>

        <TabsContent value="followers" className="mt-6">
          {followers.length === 0 ? <div className="nb-card p-12 text-center font-semibold text-slate-500" data-testid="no-followers">{t("profile.noFollowers")}</div> : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-w-4xl" data-testid="followers-list">{followers.map((u) => <UserListItem key={u.id} u={u} />)}</div>
          )}
        </TabsContent>

        <TabsContent value="following" className="mt-6">
          {following.length === 0 ? <div className="nb-card p-12 text-center font-semibold text-slate-500" data-testid="no-following">{t("profile.noFollowing")}</div> : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-w-4xl" data-testid="following-list">{following.map((u) => <UserListItem key={u.id} u={u} />)}</div>
          )}
        </TabsContent>

        <TabsContent value="settings" className="mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-4xl">
            <div className="nb-card p-6 space-y-4">
              <h3 className="font-heading font-bold text-lg">{t("profile.saveAccount")}</h3>
              <div><label className="block font-bold text-sm mb-1">{t("profile.changeName")}</label><input value={name} onChange={(e) => setName(e.target.value)} data-testid="settings-name" className="nb-input" /></div>
              <div><label className="block font-bold text-sm mb-1">{t("profile.changeEmail")}</label><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="settings-email" className="nb-input" /></div>
              <div className="flex items-start justify-between gap-3 pt-1">
                <div>
                  <div className="font-bold text-sm">{t("profile.hideFollows")}</div>
                  <div className="text-xs text-slate-500">{t("profile.hideFollowsHint")}</div>
                </div>
                <Switch checked={hideFollows} onCheckedChange={setHideFollows} data-testid="settings-hide-follows" />
              </div>
              <button onClick={saveAccount} data-testid="save-account" className="px-5 py-2.5 bg-sky-300 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press">{t("profile.saveAccount")}</button>
            </div>
            <div className="nb-card p-6 space-y-4">
              <h3 className="font-heading font-bold text-lg">{t("profile.changePassword")}</h3>
              <div><label className="block font-bold text-sm mb-1">{t("profile.currentPassword")}</label><PasswordInput value={curPw} onChange={(e) => setCurPw(e.target.value)} testId="settings-current-pw" /></div>
              <div><label className="block font-bold text-sm mb-1">{t("profile.newPassword")}</label><PasswordInput value={newPw} onChange={(e) => setNewPw(e.target.value)} testId="settings-new-pw" /></div>
              <button onClick={changePw} disabled={!curPw || newPw.length < 8} data-testid="change-password" className="px-5 py-2.5 bg-emerald-300 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press disabled:opacity-50">{t("profile.changePassword")}</button>
            </div>
            <div className="nb-card p-6 space-y-3 border-red-500 lg:col-span-2" style={{ boxShadow: "4px 4px 0px 0px rgba(239,68,68,1)" }}>
              <h3 className="font-heading font-bold text-lg text-red-600">{t("profile.dangerZone")}</h3>
              <button onClick={() => setDelOpen(true)} data-testid="delete-account" className="px-5 py-2.5 bg-red-400 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press">{t("profile.deleteAccount")}</button>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={delOpen} onOpenChange={setDelOpen}>
        <DialogContent className="border-2 border-slate-900 nb-shadow bg-white">
          <DialogHeader><DialogTitle className="font-heading">{t("profile.deleteAccount")}</DialogTitle>
          <DialogDescription>{t("profile.deleteConfirm")}</DialogDescription></DialogHeader>
          <DialogFooter className="gap-2">
            <button onClick={() => setDelOpen(false)} className="px-5 py-2.5 bg-white border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press">{t("common.cancel")}</button>
            <button onClick={deleteAcc} data-testid="confirm-delete-account" className="px-5 py-2.5 bg-red-400 border-2 border-slate-900 rounded-md font-bold nb-shadow-sm nb-press">{t("profile.deleteAccount")}</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
