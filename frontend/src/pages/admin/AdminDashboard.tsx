import { useEffect, useState, useRef } from "react";
import { Users, Activity, MessageSquare } from "lucide-react";
import { api } from "@/lib/api";
import { StatCard } from "@/components/admin/StatCard";
import { Button } from "@/components/ui/button";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import { format, addDays } from 'date-fns';

interface AdminStatsResponse {
  total_users: number;
  online_users: number;
  total_questions: number;
}

interface MetricItem {
  time: string;
  questions: number;
  users: number;
}

interface TopicItem {
  topic: string;
  count: number;
}

const TOPIC_COLORS = ['#f97316', '#3b82f6', '#10b981', '#6366f1', '#f43f5e', '#8b5cf6', '#06b6d4', '#eab308'];

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStatsResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricItem[]>([]);
  const [topics, setTopics] = useState<TopicItem[]>([]);
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [timeRange, setTimeRange] = useState<"day" | "week" | "month">("day");
  
  // Custom tracking variable to prevent full re-renders covering the whole page when only polling
  const isInitialLoad = useRef(true);
  const fetchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const fetchAllData = async (range: string = timeRange) => {
    try {
      const [statsRes, metricsRes, topicsRes] = await Promise.all([
        api.get<AdminStatsResponse>("/api/v1/admin/stats"),
        api.get<MetricItem[]>(`/api/v1/admin/metrics?range=${range}`),
        api.get<TopicItem[]>("/api/v1/admin/top-topics")
      ]);
      const formattedMetrics = metricsRes.data.map(m => {
        let label = m.time;
        try {
          const d = new Date(m.time);
          if (range === 'day') {
             label = format(d, 'dd/MM');
          } else if (range === 'week') {
             const endD = addDays(d, 6);
             label = `${format(d, 'dd')}–${format(endD, 'dd MMM')}`;
          } else if (range === 'month') {
             label = format(d, 'MMM yyyy');
          }
        } catch {}
        return { ...m, time: label };
      });
      
      setStats(statsRes.data);
      setMetrics(formattedMetrics);
      setTopics(topicsRes.data);
      setError(null);
    } catch (err: any) {
      console.error("Failed to fetch admin data:", err);
      setError("Failed to load dashboard data. Please try again later.");
    } finally {
      if (isInitialLoad.current) {
        setIsLoading(false);
        isInitialLoad.current = false;
      }
    }
  };

  const handleRangeChange = (newRange: "day" | "week" | "month") => {
    setTimeRange(newRange);
    fetchAllData(newRange);
  };

  useEffect(() => {
    // Only invoke load logic if standard range is active or ws drops
    fetchAllData(timeRange);

    let ws: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    const connectWs = () => {
      const wsUrl = process.env.NODE_ENV === "production"
        ? `wss://${window.location.host}/ws/admin`
        : "ws://127.0.0.1:8000/ws/admin";

      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "STATS_UPDATED" || data.type === "new_chat" || data.type === "user_login") {
            // Debounce the call (limit to 1 per second) to prevent reflow spam
            if (!fetchTimeoutRef.current) {
              fetchTimeoutRef.current = setTimeout(() => {
                fetchAllData(timeRange);
                fetchTimeoutRef.current = null;
              }, 1000);
            }
          }
        } catch (e) {
          console.error("Failed to parse WS message", e);
        }
      };

      ws.onclose = () => {
        reconnectTimeout = setTimeout(connectWs, 2000);
      };
      
      ws.onerror = (err) => {
        console.error("WebSocket Error:", err);
      };
    };

    connectWs();

    return () => {
      clearTimeout(reconnectTimeout);
      if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [timeRange]); // Dependency on timeRange handles websocket reconnection with fresh context

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground animate-pulse">Loading dashboard charts...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-destructive font-medium">{error}</div>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Dashboard Overview</h1>
        <p className="text-slate-500 mt-1">Real-time statistics covering user volumes and topic distributions.</p>
      </div>

      {/* STAT CARDS */}
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          title="Total Users"
          value={stats.total_users}
          icon={<Users className="text-orange-500" />}
        />
        <StatCard
          title="Online User"
          value={stats.online_users}
          icon={<Activity className="text-orange-500" />}
        />
        <StatCard
          title="Total Questions"
          value={stats.total_questions}
          icon={<MessageSquare className="text-orange-500" />}
        />
      </div>

      {/* CHARTS GRID */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* AREA CHART */}
        <div className="bg-white p-6 rounded-xl border shadow-sm flex flex-col">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div>
              <h3 className="font-semibold text-lg text-slate-800">Activity Overview</h3>
              <p className="text-sm text-slate-500">Volume of user & questions asked over time.</p>
            </div>
            
            {/* Range Toggle */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg shrink-0">
              <Button 
                size="sm" 
                variant="ghost" 
                className={`h-7 px-3 text-xs font-medium rounded-md transition-all ${timeRange === 'day' ? 'bg-white shadow-sm text-orange-600' : 'text-slate-600 hover:text-slate-900'}`}
                onClick={() => handleRangeChange('day')}
              >
                Day
              </Button>
              <Button 
                size="sm" 
                variant="ghost" 
                className={`h-7 px-3 text-xs font-medium rounded-md transition-all ${timeRange === 'week' ? 'bg-white shadow-sm text-orange-600' : 'text-slate-600 hover:text-slate-900'}`}
                onClick={() => handleRangeChange('week')}
              >
                Week
              </Button>
              <Button 
                size="sm" 
                variant="ghost" 
                className={`h-7 px-3 text-xs font-medium rounded-md transition-all ${timeRange === 'month' ? 'bg-white shadow-sm text-orange-600' : 'text-slate-600 hover:text-slate-900'}`}
                onClick={() => handleRangeChange('month')}
              >
                Month
              </Button>
            </div>
          </div>
          
          <div className="flex-1 h-[300px] w-full min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorQuestions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f97316" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorUsers" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="time" tick={{fontSize: 12, fill: '#64748b'}} tickLine={false} axisLine={false} />
                <YAxis tick={{fontSize: 12, fill: '#64748b'}} tickLine={false} axisLine={false} />
                <RechartsTooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  labelStyle={{ fontWeight: "600", color: "#0f172a" }}
                  itemStyle={{ fontSize: "14px", fontWeight: "500" }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '13px', paddingTop: '10px' }} />
                
                {/* DUAL LINE PLOTTING */}
                <Area type="monotone" dataKey="questions" name="Questions" stroke="#f97316" strokeWidth={3} fillOpacity={1} fill="url(#colorQuestions)" />
                <Area type="monotone" dataKey="users" name="Active Users" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorUsers)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* PIE CHART */}
        <div className="bg-white p-6 rounded-xl border shadow-sm flex flex-col">
          <div className="mb-4">
            <h3 className="font-semibold text-lg text-slate-800">Top Categories & Topics</h3>
            <p className="text-sm text-slate-500">Breakdown of support query types.</p>
          </div>
          <div className="flex-1 h-[300px] w-full min-h-[300px] flex justify-center items-center">
            {topics.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={topics}
                    cx="50%"
                    cy="50%"
                    innerRadius={75}
                    outerRadius={110}
                    paddingAngle={3}
                    dataKey="count"
                    nameKey="topic"
                    stroke="none"
                  >
                    {topics.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={TOPIC_COLORS[index % TOPIC_COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: "14px", fontWeight: "500" }}
                  />
                  <Legend layout="horizontal" verticalAlign="bottom" align="center" wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }}/>
                </PieChart>
              </ResponsiveContainer>
            ) : (
                <div className="flex items-center justify-center h-full w-full text-slate-400">No topic data available yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
