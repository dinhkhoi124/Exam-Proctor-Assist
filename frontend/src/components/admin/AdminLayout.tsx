import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  LogOut,
  ArrowLeft,
  Settings,
  FileText,
  FolderSync
} from "lucide-react";

export function AdminLayout() {
  const location = useLocation();
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  // For admins, allow toggling between admin and management views
  const [viewMode, setViewMode] = useState<"admin" | "manager">("manager");
  const [showToggleModal, setShowToggleModal] = useState(false);
  const [pendingViewMode, setPendingViewMode] = useState<"admin" | "manager" | null>(null);

  const handleToggleViewMode = () => {
    const nextMode = viewMode === "admin" ? "manager" : "admin";
    setPendingViewMode(nextMode);
    setShowToggleModal(true);
  };

  useEffect(() => {
    if (user?.role === "admin") {
      // If path is manager-only, stay in manager view; else default to admin
      if (location.pathname === "/admin/data" || location.pathname === "/admin/feedback") {
        setViewMode("manager");
      } else {
        setViewMode("admin");
      }
    } else {
      setViewMode("manager");
    }
  }, [user, location.pathname]);

  const handleSignOut = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const navItems = viewMode === "admin" 
    ? [
        { label: "Dashboard", href: "/admin", icon: <LayoutDashboard className="h-5 w-5" /> },
        { label: "Quản lý người dùng", href: "/admin/users", icon: <Users className="h-5 w-5" /> },
        { label: "Cài đặt hệ thống", href: "/admin/settings", icon: <Settings className="h-5 w-5" /> },
      ]
    : [
        { label: "Dashboard", href: "/admin", icon: <LayoutDashboard className="h-5 w-5" /> },
        { label: "Tài liệu", href: "/admin/data", icon: <FileText className="h-5 w-5" /> },
        { label: "Phản hồi", href: "/admin/feedback", icon: <MessageSquare className="h-5 w-5" /> },
      ];

  const sidebarTitle = viewMode === "admin" ? "FPT Admin" : "FPT Management";
  const sidebarSubtitle = "Proctor System";

  return (
    <div className="flex h-screen w-full bg-slate-50 overflow-hidden">
      {/* SIDEBAR */}
      <aside className="w-64 bg-white border-r flex flex-col justify-between hidden md:flex shrink-0">
        <div>
          <div className="h-16 flex flex-col justify-center px-6 border-b">
            <h2 className="font-bold text-lg text-orange-600 leading-tight">{sidebarTitle}</h2>
            <span className="text-xs text-slate-400 font-medium">{sidebarSubtitle}</span>
          </div>
          <nav className="p-4 space-y-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-md font-medium transition-colors ${
                    isActive
                      ? "bg-orange-100 text-orange-700"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  {item.icon}
                  {item.label}
                </Link>
              );
            })}

            {/* Toggle Area for Admins */}
            {user?.role === "admin" && (
              <div className="pt-4 mt-4 border-t border-slate-100">
                <span className="px-3 text-xxs font-bold text-slate-400 uppercase tracking-wider block mb-2">
                  {viewMode === "admin" ? "KHU VỰC MANAGEMENT" : "KHU VỰC ADMIN"}
                </span>
                <button
                  onClick={handleToggleViewMode}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-md font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
                >
                  <FolderSync className="h-5 w-5 text-orange-500" />
                  {viewMode === "admin" ? "Vào trang Management" : "Vào trang Admin"}
                </button>
              </div>
            )}
          </nav>
        </div>

        {/* BOTTOM ACTIONS */}
        <div className="p-4 border-t space-y-2">
          <Button
            variant="ghost"
            asChild
            className="w-full justify-start text-slate-600 hover:text-slate-900 hover:bg-slate-100"
          >
            <Link to="/">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Về Chat
            </Link>
          </Button>

          <Button
            variant="ghost"
            onClick={handleSignOut}
            className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50 hover:border-red-100"
          >
            <LogOut className="mr-2 h-4 w-4" />
            Đăng xuất
          </Button>
        </div>
      </aside>

      {/* MOBILE COMPATIBILITY: basic top bar for small screens */}
      <main className="flex-1 flex flex-col h-full overflow-hidden">
        <header className="h-16 md:hidden border-b bg-white flex items-center justify-between px-4 shrink-0">
          <div className="flex flex-col">
            <h2 className="font-bold text-md text-orange-600">{sidebarTitle}</h2>
            <span className="text-xxs text-slate-400 font-medium">{sidebarSubtitle}</span>
          </div>
          <div className="flex items-center gap-2">
            {user?.role === "admin" && (
              <Button size="icon" variant="ghost" onClick={handleToggleViewMode}>
                <FolderSync className="h-5 w-5 text-orange-500" />
              </Button>
            )}
            <Button size="icon" variant="ghost" onClick={handleSignOut} className="text-red-600">
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </header>

        {/* SCROLLABLE OUTLET */}
        <div className="flex-1 overflow-y-auto bg-slate-50 p-4 md:p-8">
          <Outlet />
        </div>
      </main>

      {/* View Mode Toggle Confirmation Modal */}
      {showToggleModal && pendingViewMode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white rounded-xl border shadow-lg max-w-sm w-full p-6 space-y-4 animate-in zoom-in-95 duration-200 text-left">
            <div className="space-y-1">
              <h3 className="text-base font-bold text-slate-900">
                {pendingViewMode === "manager" ? "Chuyển sang chế độ Management" : "Quay lại chế độ Admin"}
              </h3>
              <p className="text-xs text-slate-500">
                {pendingViewMode === "manager" 
                  ? "Bạn sắp chuyển sang giao diện Management." 
                  : "Bạn sắp quay lại giao diện Admin."}
              </p>
              <p className="text-xs font-semibold text-slate-700">Tiếp tục?</p>
            </div>
            <div className="flex items-center justify-end gap-2 pt-2">
              <Button 
                variant="ghost" 
                onClick={() => { setShowToggleModal(false); setPendingViewMode(null); }}
                className="text-xs font-semibold text-slate-600 border bg-white hover:bg-slate-50 h-8 px-3"
              >
                Hủy
              </Button>
              <Button 
                onClick={() => {
                  setViewMode(pendingViewMode);
                  setShowToggleModal(false);
                  setPendingViewMode(null);
                }}
                className="bg-orange-600 hover:bg-orange-700 text-white text-xs font-semibold h-8 px-3"
              >
                Xác nhận
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
