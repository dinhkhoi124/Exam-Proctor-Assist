// import { Link, useLocation } from "react-router-dom";
// import { MessageSquare, Info, GraduationCap, LogOut } from "lucide-react";
// import { cn } from "@/lib/utils";
// import { useAuth } from "@/context/AuthContext";
// import { Button } from "@/components/ui/button";

// export function Header() {
//   const location = useLocation();
//   const { user, logout } = useAuth();

//   const navItems = [
//     { path: "/", label: "Chat", icon: MessageSquare },
//     { path: "/about", label: "About", icon: Info },
//   ];

//   return (
//     <header className="sticky top-0 z-50 w-full border-b border-border bg-card/80 backdrop-blur-md">
//       <div className="container flex h-16 items-center justify-between px-4 md:px-6">
//         {/* Logo */}
//         <Link
//           to="/"
//           className="flex items-center gap-3 transition-opacity hover:opacity-80"
//         >
//           <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary shadow-md">
//             <GraduationCap className="h-5 w-5 text-primary-foreground" />
//           </div>

//           <div className="flex flex-col">
//             <span className="text-lg font-bold leading-tight text-foreground">
//               FPT Exam Support
//             </span>
//             <span className="text-xs text-muted-foreground">
//               Proctor Assistant
//             </span>
//           </div>
//         </Link>

//         {/* Navigation */}
//         <nav className="flex items-center gap-1">
//           {navItems.map((item) => {
//             const Icon = item.icon;
//             const isActive = location.pathname === item.path;

//             return (
//               <Link
//                 key={item.path}
//                 to={item.path}
//                 className={cn(
//                   "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
//                   isActive
//                     ? "bg-primary text-primary-foreground"
//                     : "text-muted-foreground hover:bg-secondary hover:text-foreground",
//                 )}
//               >
//                 <Icon className="h-4 w-4" />
//                 <span className="hidden sm:inline">{item.label}</span>
//               </Link>
//             );
//           })}

//           {/* Logout */}
//           {user && (
//             <Button
//               variant="ghost"
//               size="sm"
//               onClick={logout}
//               className="ml-2 text-muted-foreground hover:text-foreground"
//             >
//               <LogOut className="h-4 w-4" />
//               <span className="hidden sm:inline">Sign Out</span>
//             </Button>
//           )}
//         </nav>
//       </div>
//     </header>
//   );
// }

import { Link, useLocation } from "react-router-dom";
import { MessageSquare, Info, GraduationCap, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

export function Header() {
  const location = useLocation();
  const { isAuthenticated, logout } = useAuth();

  const navItems = [
    { path: "/", label: "Chat", icon: MessageSquare },
    { path: "/about", label: "About", icon: Info },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-card/80 backdrop-blur-md">
      <div className="container flex h-16 items-center justify-between px-4 md:px-6">
        {/* Logo */}
        <Link
          to="/"
          className="flex items-center gap-3 transition-opacity hover:opacity-80"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary shadow-md">
            <GraduationCap className="h-5 w-5 text-primary-foreground" />
          </div>

          <div className="flex flex-col">
            <span className="text-lg font-bold leading-tight text-foreground">
              FPT Exam Support
            </span>
            <span className="text-xs text-muted-foreground">
              Proctor Assistant
            </span>
          </div>
        </Link>

        {/* Navigation */}
        <nav className="flex items-center gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}

          {/* Logout */}
          {isAuthenticated && (
            <Button
              variant="ghost"
              size="sm"
              onClick={logout}
              className="ml-2 text-muted-foreground hover:text-foreground"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Sign Out</span>
            </Button>
          )}
        </nav>
      </div>
    </header>
  );
}
