import { Link, useLocation } from "react-router-dom";
import { MessageSquare, Info, GraduationCap, LogOut, Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/auth";
import { Button } from "@/components/ui/button";

export function Header() {
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuth();

  const navItems = [
    { path: "/", label: "Chat", icon: MessageSquare },
    { path: "/about", label: "About", icon: Info },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-card/80 backdrop-blur-md">
      <div className="flex h-16 w-full min-w-0 items-center justify-between gap-2 px-3 sm:px-4 lg:px-5">
        {/* Logo */}
        <Link
          to="/"
          aria-label="FPT Exam Support"
          className="flex min-w-0 shrink-0 items-center gap-2.5 transition-opacity hover:opacity-80 sm:gap-3"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary shadow-md">
            <GraduationCap className="h-5 w-5 text-primary-foreground" />
          </div>

          <div className="hidden min-w-0 flex-col min-[375px]:flex">
            <span className="text-base font-bold leading-tight text-foreground sm:text-lg">
              FPT Exam Support
            </span>
            <span className="text-xs text-muted-foreground">
              Proctor Assistant
            </span>
          </div>
        </Link>

        {/* Navigation */}
        <nav className="flex shrink-0 items-center gap-0.5 sm:gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <Link
                key={item.path}
                to={item.path}
                aria-label={item.label}
                className={cn(
                  "flex items-center gap-2 rounded-lg p-2 text-sm font-medium transition-colors lg:px-4",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden lg:inline">{item.label}</span>
              </Link>
            );
          })}

          {(user?.role === "admin" || user?.role === "manager") && (
            <Link
              to="/admin"
              aria-label={user.role === "admin" ? "Admin" : "Management"}
              className={cn(
                "flex items-center gap-2 rounded-lg p-2 text-sm font-medium transition-colors lg:px-4",
                location.pathname.startsWith("/admin")
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              )}
            >
              <Shield className="h-4 w-4" />
              <span className="hidden lg:inline">
                {user.role === "admin" ? "Admin" : "Management"}
              </span>
            </Link>
          )}

          {/* Logout */}
          {isAuthenticated && (
            <Button
              variant="ghost"
              size="sm"
              onClick={logout}
              aria-label="Sign Out"
              className="ml-0 px-2 text-muted-foreground hover:text-foreground lg:ml-2 lg:px-3"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden lg:inline">Sign Out</span>
            </Button>
          )}
        </nav>
      </div>
    </header>
  );
}
