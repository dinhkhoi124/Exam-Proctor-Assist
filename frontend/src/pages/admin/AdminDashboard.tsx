import { useEffect, useState } from "react";
import { Users, Activity, MessageSquare, LogOut } from "lucide-react";
import { api } from "@/lib/api";
import { StatCard } from "@/components/admin/StatCard";
import { UsersTable } from "@/components/admin/UsersTable";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

interface AdminStatsResponse {
  total_users: number;
  online_users: number;
  total_questions: number;
  users: {
    email: string;
    question_count: number;
  }[];
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStatsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleSignOut = () => {
    logout();
    navigate("/login", { replace: true });
  };

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.get<AdminStatsResponse>("/api/v1/admin/stats");
        setStats(response.data);
        setError(null);
      } catch (err: any) {
        console.error("Failed to fetch admin stats:", err);
        setError("Failed to load dashboard data. Please try again later.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
        <div className="text-muted-foreground">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
        <div className="text-destructive">{error}</div>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="container mx-auto p-6 space-y-8 animate-in fade-in duration-500">
      {/* HEADER SECTION */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between rounded-xl bg-orange-100 border-l-8 border-orange-500 p-6 shadow-sm">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-black">Admin Dashboard</h1>
          <p className="text-black mt-1 opacity-80">Overview of system statistics and user data.</p>
        </div>
        
        <div className="flex items-center gap-3 mt-4 sm:mt-0">
          <Button
            variant="outline"
            asChild
            className="bg-white text-black hover:bg-orange-50 hover:text-orange-600 border-orange-200 transition-colors"
          >
            <Link to="/">
              <MessageSquare className="mr-2 h-4 w-4" />
              Back to Chat
            </Link>
          </Button>
          <Button
            variant="default"
            onClick={handleSignOut}
            className="bg-orange-500 hover:bg-orange-600 text-white transition-colors"
          >
            <LogOut className="mr-2 h-4 w-4" />
            Sign Out
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          title="Total Users"
          value={stats.total_users}
          icon={<Users />}
        />
        <StatCard
          title="Online Users"
          value={stats.online_users}
          icon={<Activity />}
        />
        <StatCard
          title="Total Questions"
          value={stats.total_questions}
          icon={<MessageSquare />}
        />
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold tracking-tight">Users Activity</h2>
        <UsersTable users={stats.users || []} />
      </div>
    </div>
  );
}
