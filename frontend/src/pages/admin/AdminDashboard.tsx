import { useEffect, useState, useRef } from "react";
import { Users, Activity, MessageSquare, FileText, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import { StatCard } from "@/components/admin/StatCard";
import { Button } from "@/components/ui/button";
import {
  LineChart, Line, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend
} from 'recharts';
import { format } from 'date-fns';

interface AdminStatsResponse {
  total_users: number;
  online_users: number;
  total_questions: number;
  total_feedbacks?: number;
  feedback_distribution?: {
    like: number;
    dislike: number;
  };
}

interface MetricItem {
  time: string;
  questions: number;
  users: number;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStatsResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<"day" | "month" | "year">("day");
  
  const isInitialLoad = useRef(true);
  const fetchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const fetchAllData = async (range: string = timeRange) => {
    try {
      const [statsRes, metricsRes] = await Promise.all([
        api.get<AdminStatsResponse>("/api/v1/admin/stats"),
        api.get<MetricItem[]>(`/api/v1/admin/metrics?range=${range}`)
      ]);
      
      const formattedMetrics = metricsRes.data.map(m => {
        let label = m.time;
        try {
          const d = new Date(m.time);
          if (range === 'day') {
             label = format(d, 'dd/MM');
          } else if (range === 'month') {
             label = format(d, 'MM/yyyy');
          } else if (range === 'year') {
             label = format(d, 'yyyy');
          }
        } catch {}
        return { ...m, time: label };
      });
      
      setStats(statsRes.data);
      setMetrics(formattedMetrics);
      setError(null);
    } catch (err: any) {
      console.error("Failed to fetch admin data:", err);
      setError("Không thể tải dữ liệu bảng điều khiển. Vui lòng thử lại sau.");
    } finally {
      if (isInitialLoad.current) {
        setIsLoading(false);
        isInitialLoad.current = false;
      }
    }
  };

  const handleRangeChange = (newRange: "day" | "month" | "year") => {
    setTimeRange(newRange);
    fetchAllData(newRange);
  };

  useEffect(() => {
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
  }, [timeRange]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground animate-pulse font-medium">Đang tải biểu đồ thống kê...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2 font-medium border border-red-100">
          <AlertCircle className="h-5 w-5" />
          {error}
        </div>
      </div>
    );
  }

  if (!stats) return null;

  // Chart Title Subtext
  const rangeLabel = timeRange === "day" ? "ngày" : timeRange === "month" ? "tháng" : "năm";

  // Data for Feedback rating distribution BarChart
  const feedbackData = [
    {
      name: "Hài lòng (Like)",
      value: stats.feedback_distribution?.like || 0,
      color: "#22c55e"
    },
    {
      name: "Chưa hài lòng (Dislike)",
      value: stats.feedback_distribution?.dislike || 0,
      color: "#ef4444"
    }
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Bảng điều khiển</h1>
        <p className="text-slate-500 mt-1">Tổng quan hệ thống AI Proctor.</p>
      </div>

      {/* STAT CARDS */}
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          title="Tổng người dùng"
          value={stats.total_users}
          icon={<Users className="text-orange-500 h-5 w-5" />}
        />
        <StatCard
          title="Lượt hỏi (ngày)"
          value={stats.total_questions}
          icon={<Activity className="text-orange-500 h-5 w-5" />}
        />
        <div className="bg-white p-6 rounded-xl border shadow-sm relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-500">Tài liệu</span>
            <FileText className="text-orange-500 h-5 w-5" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-semibold tracking-tight text-slate-900">0</span>
            <span className="text-xxs font-bold px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded-md">
              Pending
            </span>
          </div>
        </div>
        <StatCard
          title="Phản hồi"
          value={stats.total_feedbacks !== undefined ? stats.total_feedbacks : 0}
          icon={<MessageSquare className="text-orange-500 h-5 w-5" />}
        />
      </div>

      {/* CHARTS GRID */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* LINE CHART */}
        <div className="bg-white p-6 rounded-xl border shadow-sm flex flex-col">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div>
              <h3 className="font-semibold text-lg text-slate-800">
                Câu hỏi theo {rangeLabel}
              </h3>
              <p className="text-sm text-slate-500">Thống kê lượng người dùng & câu hỏi gửi lên.</p>
            </div>
            
            {/* Range Toggle */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg shrink-0">
              <Button 
                size="sm" 
                variant="ghost" 
                className={`h-7 px-3 text-xs font-semibold rounded-md transition-all ${timeRange === 'day' ? 'bg-white shadow-sm text-orange-600' : 'text-slate-600 hover:text-slate-900'}`}
                onClick={() => handleRangeChange('day')}
              >
                Ngày
              </Button>
              <Button 
                size="sm" 
                variant="ghost" 
                className={`h-7 px-3 text-xs font-semibold rounded-md transition-all ${timeRange === 'month' ? 'bg-white shadow-sm text-orange-600' : 'text-slate-600 hover:text-slate-900'}`}
                onClick={() => handleRangeChange('month')}
              >
                Tháng
              </Button>
              <Button 
                size="sm" 
                variant="ghost" 
                className={`h-7 px-3 text-xs font-semibold rounded-md transition-all ${timeRange === 'year' ? 'bg-white shadow-sm text-orange-600' : 'text-slate-600 hover:text-slate-900'}`}
                onClick={() => handleRangeChange('year')}
              >
                Năm
              </Button>
            </div>
          </div>
          
          <div className="flex-1 h-[300px] w-full min-h-[300px]">
            {metrics.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={metrics} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="time" tick={{fontSize: 12, fill: '#64748b'}} tickLine={false} axisLine={false} />
                  <YAxis tick={{fontSize: 12, fill: '#64748b'}} tickLine={false} axisLine={false} />
                  <RechartsTooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    labelStyle={{ fontWeight: "600", color: "#0f172a" }}
                    itemStyle={{ fontSize: "14px", fontWeight: "500" }}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: '13px', paddingTop: '10px' }} />
                  
                  <Line type="monotone" dataKey="questions" name="Số câu hỏi" stroke="#f97316" strokeWidth={3} activeDot={{ r: 6 }} dot={{ strokeWidth: 2 }} />
                  <Line type="monotone" dataKey="users" name="Người dùng hoạt động" stroke="#3b82f6" strokeWidth={3} activeDot={{ r: 6 }} dot={{ strokeWidth: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full w-full text-slate-400 text-sm">
                Không có dữ liệu hoạt động.
              </div>
            )}
          </div>
        </div>

        {/* BAR CHART (FEEDBACK RATING) */}
        <div className="bg-white p-6 rounded-xl border shadow-sm flex flex-col">
          <div className="mb-4">
            <h3 className="font-semibold text-lg text-slate-800">
              Phân bố đánh giá
            </h3>
            <p className="text-sm text-slate-500">Mức độ hài lòng của Giám thị đối với chatbot.</p>
          </div>
          
          <div className="flex-1 h-[300px] w-full min-h-[300px]">
            {stats.total_feedbacks !== undefined && stats.total_feedbacks > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={feedbackData} margin={{ top: 20, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{fontSize: 12, fill: '#64748b'}} tickLine={false} axisLine={false} />
                  <YAxis tick={{fontSize: 12, fill: '#64748b'}} tickLine={false} axisLine={false} allowDecimals={false} />
                  <RechartsTooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    cursor={{ fill: 'rgba(241, 245, 249, 0.4)' }}
                  />
                  <Bar dataKey="value" name="Số lượt đánh giá" radius={[8, 8, 0, 0]} maxBarSize={60}>
                    {feedbackData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-full w-full border border-dashed rounded-xl bg-slate-50/50 p-6 text-center text-slate-400">
                <MessageSquare className="h-12 w-12 text-slate-350 mb-2" />
                <span className="text-sm font-semibold text-slate-500 mb-0.5">Không có dữ liệu đánh giá</span>
                <p className="text-xs text-slate-400 max-w-[240px]">
                  Giám thị chưa thực hiện đánh giá Thích/Không thích nào đối với câu trả lời của chatbot.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

