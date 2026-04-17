import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import {
  LayoutDashboard,
  Users,
  PieChart,
  MessageSquare,
  LogOut,
  ArrowLeft
} from "lucide-react";

export function AdminLayout() {
  const location = useLocation();
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleSignOut = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const navItems = [
    { label: "Dashboard", href: "/admin", icon: <LayoutDashboard className="h-5 w-5" /> },
    { label: "User Management", href: "/admin/users", icon: <Users className="h-5 w-5" /> },
    { label: "Topic Analytics", href: "/admin/data", icon: <PieChart className="h-5 w-5" /> },
    { label: "Feedback", href: "/admin/feedback", icon: <MessageSquare className="h-5 w-5" /> },
  ];

  return (
    <div className="flex h-screen w-full bg-slate-50 overflow-hidden">
      {/* SIDEBAR */}
      <aside className="w-64 bg-white border-r flex flex-col justify-between hidden md:flex shrink-0">
        <div>
          <div className="h-16 flex items-center px-6 border-b">
            <h2 className="font-bold text-xl text-orange-600">Admin Panel</h2>
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
              Back to Chat
            </Link>
          </Button>

          <Button
            variant="ghost"
            onClick={handleSignOut}
            className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50 hover:border-red-100"
          >
            <LogOut className="mr-2 h-4 w-4" />
            Sign Out
          </Button>
        </div>
      </aside>

      {/* MOBILE COMPATIBILITY: basic top bar for small screens if needed, otherwise rely on desktop */}
      
      {/* MAIN CONTENT V-STACK */}
      <main className="flex-1 flex flex-col h-full overflow-hidden">
        {/* TOP BAR / BREADCRUMB area if needed */}
        <header className="h-16 md:hidden border-b bg-white flex items-center justify-between px-4 shrink-0">
          <h2 className="font-bold text-lg text-orange-600">Admin Panel</h2>
          <Button size="icon" variant="ghost" onClick={handleSignOut} className="text-red-600">
            <LogOut className="h-5 w-5" />
          </Button>
        </header>

        {/* SCROLLABLE OUTLET */}
        <div className="flex-1 overflow-y-auto bg-slate-50 p-4 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
