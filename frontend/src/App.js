import "@/App.css";
import "@/i18n";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import { Header } from "@/components/Header";
import Feed from "@/pages/Feed";
import AssignmentView from "@/pages/AssignmentView";
import Publish from "@/pages/Publish";
import Profile from "@/pages/Profile";
import Admin from "@/pages/Admin";
import Login from "@/pages/Login";
import Register from "@/pages/Register";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen">
          <Header />
          <main>
            <Routes>
              <Route path="/" element={<Feed />} />
              <Route path="/assignment/:id" element={<AssignmentView />} />
              <Route path="/publish" element={<Publish />} />
              <Route path="/edit/:id" element={<Publish />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
            </Routes>
          </main>
        </div>
        <Toaster position="top-center" />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
