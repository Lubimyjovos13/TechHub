import "@/App.css";
import "@/i18n";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import { Header } from "@/components/Header";
import Feed from "@/pages/Feed";
import AssignmentView from "@/pages/AssignmentView";
import Publish from "@/pages/Publish";
import Profile from "@/pages/Profile";
import PublicProfile from "@/pages/PublicProfile";
import Workspace from "@/pages/Workspace";
import Admin from "@/pages/Admin";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";

function Shell() {
  const location = useLocation();
  const hideHeader = location.pathname === "/workspace";
  return (
    <div className="min-h-screen">
      {!hideHeader && <Header />}
      <main>
        <Routes>
          <Route path="/" element={<Feed />} />
          <Route path="/assignment/:id" element={<AssignmentView />} />
          <Route path="/publish" element={<Publish />} />
          <Route path="/edit/:id" element={<Publish />} />
          <Route path="/workspace" element={<Workspace />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/u/:id" element={<PublicProfile />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Shell />
        <Toaster
          position="top-center"
          toastOptions={{
            style: {
              background: "var(--nb-surface)",
              color: "var(--nb-text)",
              border: "2px solid var(--nb-border)",
              boxShadow: "4px 4px 0px 0px var(--nb-shadow)",
              fontWeight: 600,
            },
          }}
        />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
