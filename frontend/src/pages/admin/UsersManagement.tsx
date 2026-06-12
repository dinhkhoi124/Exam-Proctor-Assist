import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import { format } from "date-fns";
import { Clock, MessageSquare, Search, Filter, ShieldAlert, ArrowLeftRight, UserCheck, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface UserItem {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_active: string | null;
  question_count: number;
}

interface ChatLogItem {
  id: string;
  user_id: string;
  username: string;
  email: string;
  question: string;
  answer: string;
  topic: string;
  created_at: string;
  session_title?: string | null;
}

interface ChatLogsResponse {
  items: ChatLogItem[];
  page: number;
  limit: number;
  total: number;
  has_next: boolean;
}

export default function UsersManagement() {
  const [activeTab, setActiveTab] = useState<"users" | "logs">("users");
  
  // Data lists
  const [users, setUsers] = useState<UserItem[]>([]);
  const [chatLogs, setChatLogs] = useState<ChatLogItem[]>([]);
  
  // Loaders
  const [isUsersLoading, setIsUsersLoading] = useState(true);
  const [isLogsLoading, setIsLogsLoading] = useState(false);
  
  // Filters & Pagination state
  const [searchSearch, setSearchSearch] = useState("");
  const [userFilter, setUserFilter] = useState("all");
  const [userSearchText, setUserSearchText] = useState("");
  const [topicFilter, setTopicFilter] = useState("all");
  const [timeFilter, setTimeFilter] = useState("all");
  const [sortOrder, setSortOrder] = useState("desc");
  const [page, setPage] = useState(1);
  const [totalLogs, setTotalLogs] = useState(0);
  const [hasNextLogs, setHasNextLogs] = useState(false);
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const limitLogs = 50;

  // Role change confirmation state
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [roleChangeUser, setRoleChangeUser] = useState<UserItem | null>(null);
  const [pendingRole, setPendingRole] = useState<string>("");

  const fetchUsers = async (silent: boolean = false) => {
    try {
      if (!silent) {
        setIsUsersLoading(true);
      }
      const res = await api.get<UserItem[]>("/api/v1/admin/users");
      setUsers(res.data);
    } catch (err) {
      console.error("Failed to fetch users", err);
      toast.error("Không thể tải danh sách người dùng");
    } finally {
      if (!silent) {
        setIsUsersLoading(false);
      }
    }
  };

  const fetchUsersRef = useRef(fetchUsers);
  useEffect(() => {
    fetchUsersRef.current = fetchUsers;
  });

  const formatLastActive = (dateStr: string | null) => {
    if (!dateStr) return "Chưa hoạt động";
    try {
      return format(new Date(dateStr), "dd/MM/yyyy HH:mm");
    } catch {
      return "Chưa hoạt động";
    }
  };

  const handleSelectRoleChange = (u: UserItem, newRole: string) => {
    if (u.role === newRole) return;
    setRoleChangeUser(u);
    setPendingRole(newRole);
    setShowRoleModal(true);
  };

  const confirmRoleChange = async () => {
    if (!roleChangeUser || !pendingRole) return;
    
    const userId = roleChangeUser.id;
    const previousUsers = users;
    
    // Optimistic update
    setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: pendingRole } : u));
    setShowRoleModal(false);
    
    try {
      await api.put(`/api/v1/admin/users/${userId}/role`, { role: pendingRole });
      toast.success("Cập nhật phân quyền thành công");
      fetchUsers(true);
    } catch (err: any) {
      console.error("Failed to update user role", err);
      toast.error(err.response?.data?.detail || "Không thể cập nhật phân quyền");
      setUsers(previousUsers);
    } finally {
      setRoleChangeUser(null);
      setPendingRole("");
    }
  };

  const fetchChatLogs = async (silent: boolean = false) => {
    try {
      if (!silent) {
        setIsLogsLoading(true);
      }
      const params = new URLSearchParams();
      if (userFilter && userFilter !== "all") params.append("user_id", userFilter);
      if (userSearchText) params.append("query", userSearchText);
      if (topicFilter && topicFilter !== "all") params.append("topic", topicFilter);
      if (timeFilter && timeFilter !== "all") params.append("range", timeFilter);
      params.append("sort_order", sortOrder);
      params.append("page", String(page));
      params.append("limit", String(limitLogs));
      
      const res = await api.get<ChatLogsResponse>(`/api/v1/admin/chat-logs?${params.toString()}`);
      setChatLogs(res.data.items);
      setTotalLogs(res.data.total);
      setHasNextLogs(res.data.has_next);
    } catch (err) {
      console.error("Failed to fetch chat logs", err);
      toast.error("Không thể tải nhật ký hoạt động");
    } finally {
      if (!silent) {
        setIsLogsLoading(false);
      }
    }
  };

  // Keep a reference to fetchChatLogs to avoid stale closures in WebSocket useEffect
  const fetchChatLogsRef = useRef(fetchChatLogs);
  useEffect(() => {
    fetchChatLogsRef.current = fetchChatLogs;
  });

  const handleUpdateRole = async (userId: string, newRole: string) => {
    try {
      const res = await api.put(`/api/v1/admin/users/${userId}/role`, { role: newRole });
      toast.success(`Cập nhật vai trò người dùng thành công`);
      fetchUsers();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Không thể thay đổi vai trò");
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // Reset page and collapse expanded log on filter change
  const handleFilterChange = (setter: (val: any) => void, val: any) => {
    setter(val);
    setPage(1);
    setExpandedLogId(null);
  };

  // Trigger loading when activeTab, dropdown filters or page changes
  useEffect(() => {
    if (activeTab === "logs") {
      fetchChatLogs();
    }
  }, [activeTab, userFilter, topicFilter, timeFilter, sortOrder, page]);

  // WebSocket Integration for real-time updates
  const fetchLogsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  useEffect(() => {
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
          // Refresh on stats updates or when a new chat log is created
          if (data.type === "CHAT_LOG_CREATED" || data.type === "STATS_UPDATED") {
            if (!fetchLogsTimeoutRef.current) {
              fetchLogsTimeoutRef.current = setTimeout(() => {
                if (activeTab === "logs") {
                  fetchChatLogsRef.current(true);
                } else {
                  fetchUsersRef.current(true);
                }
                fetchLogsTimeoutRef.current = null;
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
      if (fetchLogsTimeoutRef.current) clearTimeout(fetchLogsTimeoutRef.current);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [activeTab]);

  const handleLogSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setExpandedLogId(null);
    fetchChatLogs();
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    setExpandedLogId(null);
  };

  // Filter user list for table search
  const filteredUsersList = users.filter(u => 
    u.username.toLowerCase().includes(searchSearch.toLowerCase()) ||
    u.email.toLowerCase().includes(searchSearch.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Quản lý người dùng</h1>
        <p className="text-slate-500 mt-1">Phân quyền, thăng cấp/hạ cấp người dùng và xem nhật ký hoạt động.</p>
      </div>

      {/* TABS CONTAINER */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab("users")}
          className={`px-5 py-3 font-semibold text-sm transition-all border-b-2 -mb-[2px] flex items-center gap-2 ${
            activeTab === "users"
              ? "border-orange-600 text-orange-600"
              : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          <UserCheck className="h-4 w-4" />
          Người dùng
        </button>
        <button
          onClick={() => setActiveTab("logs")}
          className={`px-5 py-3 font-semibold text-sm transition-all border-b-2 -mb-[2px] flex items-center gap-2 ${
            activeTab === "logs"
              ? "border-orange-600 text-orange-600"
              : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          <Clock className="h-4 w-4" />
          Nhật ký hoạt động
        </button>
      </div>

      {/* USER LIST TAB */}
      {activeTab === "users" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="relative w-72">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Tìm theo tên, email..."
                value={searchSearch}
                onChange={(e) => setSearchSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 rounded-lg border text-sm focus:outline-none focus:ring-1 focus:ring-orange-500 focus:border-orange-500 bg-white"
              />
            </div>
            <span className="text-xs text-slate-500 font-medium">
              Đang hiển thị {filteredUsersList.length} trên tổng số {users.length} người dùng
            </span>
          </div>

          <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-50 text-slate-500 border-b">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Họ tên</th>
                    <th className="px-6 py-4 font-semibold">Email</th>
                    <th className="px-6 py-4 font-semibold">Vai trò</th>
                    <th className="px-6 py-4 font-semibold text-center">Câu hỏi</th>
                    <th className="px-6 py-4 font-semibold">Tạo lúc</th>
                    <th className="px-6 py-4 font-semibold">Hoạt động cuối</th>
                    <th className="px-6 py-4 font-semibold text-right">Thay đổi vai trò</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {isUsersLoading ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-8 text-center text-slate-400 animate-pulse">
                        Đang tải danh sách người dùng...
                      </td>
                    </tr>
                  ) : filteredUsersList.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-8 text-center text-slate-400">
                        Không tìm thấy người dùng phù hợp.
                      </td>
                    </tr>
                  ) : (
                    filteredUsersList.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-6 py-4 font-medium text-slate-900">
                          <div className="flex flex-col">
                            <span>{u.username}</span>
                            <span className="text-xxs text-slate-400 font-normal">@{u.username.toLowerCase()}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-slate-500 font-normal">{u.email}</td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xxs font-bold ${
                            u.role === 'admin' 
                              ? 'bg-red-100 text-red-700' 
                              : u.role === 'manager' 
                                ? 'bg-indigo-100 text-indigo-700' 
                                : 'bg-slate-100 text-slate-700'
                          }`}>
                            {u.role === 'admin' ? 'Admin' : u.role === 'manager' ? 'Management' : 'User'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-orange-50 text-orange-700">
                            {u.question_count}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-slate-400 text-xs">
                          {format(new Date(u.created_at), "dd/MM/yyyy")}
                        </td>
                        <td className="px-6 py-4 text-slate-400 text-xs">
                          {formatLastActive(u.last_active)}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <select
                            value={u.role}
                            onChange={(e) => handleSelectRoleChange(u, e.target.value)}
                            className="text-xs bg-white border rounded px-2 py-1 text-slate-700 font-medium hover:border-slate-300 focus:outline-none focus:ring-1 focus:ring-orange-500"
                          >
                            <option value="user">User</option>
                            <option value="manager">Management</option>
                            <option value="admin">Admin</option>
                          </select>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ACTIVITY LOGS TAB */}
      {activeTab === "logs" && (
        <div className="space-y-6">
          {/* Filters Form */}
          <form onSubmit={handleLogSearchSubmit} className="grid gap-4 md:grid-cols-5 bg-white p-4 rounded-xl border shadow-sm items-end">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-600 block">Tìm kiếm</label>
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Nội dung Q&A..."
                  value={userSearchText}
                  onChange={(e) => setUserSearchText(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 rounded-lg border text-sm focus:outline-none focus:ring-1 focus:ring-orange-500 bg-white"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-600 block">Người dùng</label>
              <select
                value={userFilter}
                onChange={(e) => handleFilterChange(setUserFilter, e.target.value)}
                className="w-full px-3 py-2 rounded-lg border text-sm bg-white focus:outline-none focus:ring-1 focus:ring-orange-500 text-slate-700"
              >
                <option value="all">Tất cả người dùng</option>
                {users.map(u => (
                  <option key={u.id} value={u.id}>{u.username}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-600 block">Chủ đề (Topic)</label>
              <select
                value={topicFilter}
                onChange={(e) => handleFilterChange(setTopicFilter, e.target.value)}
                className="w-full px-3 py-2 rounded-lg border text-sm bg-white focus:outline-none focus:ring-1 focus:ring-orange-500 text-slate-700"
              >
                <option value="all">Tất cả chủ đề</option>
                <option value="Login & Account Issues">Login & Account Issues</option>
                <option value="Exam System Errors">Exam System Errors</option>
                <option value="Submission Problems">Submission Problems</option>
                <option value="Network & Connection Issues">Network & Connection Issues</option>
                <option value="Device & Hardware Issues">Device & Hardware Issues</option>
                <option value="Exam Regulations & Violations">Exam Regulations & Violations</option>
                <option value="Proctoring & Monitoring">Proctoring & Monitoring</option>
                <option value="Emergency Situations">Emergency Situations</option>
                <option value="General Guidance">General Guidance</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-600 block">Thời gian</label>
              <select
                value={timeFilter}
                onChange={(e) => handleFilterChange(setTimeFilter, e.target.value)}
                className="w-full px-3 py-2 rounded-lg border text-sm bg-white focus:outline-none focus:ring-1 focus:ring-orange-500 text-slate-700"
              >
                <option value="all">Tất cả thời gian</option>
                <option value="day">Hôm nay</option>
                <option value="month">Tháng này</option>
                <option value="year">Năm nay</option>
              </select>
            </div>

            <div className="flex gap-2">
              <div className="flex-1 space-y-1.5">
                <label className="text-xs font-semibold text-slate-600 block">Sắp xếp</label>
                <select
                  value={sortOrder}
                  onChange={(e) => handleFilterChange(setSortOrder, e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border text-sm bg-white focus:outline-none focus:ring-1 focus:ring-orange-500 text-slate-700"
                >
                  <option value="desc">Mới nhất trước</option>
                  <option value="asc">Cũ nhất trước</option>
                </select>
              </div>
              <Button type="submit" className="bg-orange-600 hover:bg-orange-700 text-white shrink-0 h-10 px-4 self-end">
                Tìm
              </Button>
            </div>
          </form>

          {/* Logs List Container */}
          <div className="space-y-4">
            {isLogsLoading ? (
              <div className="bg-white p-8 rounded-xl border text-center text-slate-400 animate-pulse font-medium">
                Đang tải nhật ký hội thoại...
              </div>
            ) : chatLogs.length === 0 ? (
              <div className="bg-white p-12 rounded-xl border text-center text-slate-400">
                Không tìm thấy hội thoại nào ghi nhận.
              </div>
            ) : (
              <div className="space-y-4">
                {chatLogs.map((log) => {
                  const isExpanded = expandedLogId === log.id;
                  const sessionName = log.session_title 
                    ? `[${log.session_title}]` 
                    : `[Cuộc trò chuyện không tiêu đề]`;
                  
                  const questionPreview = log.question.length > 80 
                    ? log.question.slice(0, 80) + "..." 
                    : log.question;
                    
                  return (
                    <div key={log.id} className="bg-white rounded-xl border shadow-sm overflow-hidden flex flex-col transition-all duration-205">
                      {/* Summary Row */}
                      <div 
                        onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                        className="px-5 py-3.5 flex items-center justify-between cursor-pointer hover:bg-slate-50/70 transition-colors select-none flex-wrap gap-4 text-xs"
                      >
                        <div className="flex items-center gap-2.5 min-w-[180px]">
                          <div className="h-6 w-6 rounded-full bg-orange-100 flex items-center justify-center font-bold text-orange-600 text-xxs">
                            {log.username.slice(0, 2).toUpperCase()}
                          </div>
                          <div className="flex flex-col">
                            <span className="font-bold text-slate-800">{log.username}</span>
                            <span className="text-[10px] text-slate-400 font-normal">{log.email}</span>
                          </div>
                        </div>

                        {/* Session & Question Preview */}
                        <div className="flex-1 min-w-[240px] px-2 text-slate-500 font-medium truncate">
                          <span className="text-slate-800 font-semibold mr-1.5">{sessionName}</span>
                          <span className="italic text-xs font-normal">"{questionPreview}"</span>
                        </div>

                        {/* Badges & Actions */}
                        <div className="flex items-center gap-3 shrink-0 ml-auto font-medium">
                          <span className="px-2 py-0.5 bg-orange-50 text-orange-700 font-bold rounded text-[10px] uppercase tracking-wider">
                            {log.topic || "General Guidance"}
                          </span>
                          <span className="flex items-center gap-1 text-slate-400">
                            <Clock className="h-3 w-3" />
                            {format(new Date(log.created_at), "dd/MM/yyyy HH:mm")}
                          </span>
                          <button className="text-orange-600 hover:text-orange-700 font-bold flex items-center gap-1 pl-1">
                            {isExpanded ? "Thu gọn" : "Xem chi tiết"}
                            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                          </button>
                        </div>
                      </div>

                      {/* Expanded Content Accordion */}
                      {isExpanded && (
                        <div className="px-6 pb-6 pt-3 border-t bg-slate-50/20 space-y-4 animate-in slide-in-from-top-2 duration-200">
                          {/* Question Bubble */}
                          <div className="flex gap-3 items-start max-w-[85%]">
                            <div className="h-7 w-7 rounded-full bg-slate-100 flex items-center justify-center font-bold text-slate-500 text-[10px] shrink-0 border">
                              US
                            </div>
                            <div className="flex flex-col gap-1">
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Giám thị</span>
                              <div className="p-3 bg-slate-100 rounded-2xl rounded-tl-none text-slate-800 text-sm font-medium leading-relaxed shadow-xs">
                                {log.question}
                              </div>
                            </div>
                          </div>

                          {/* Answer Bubble */}
                          <div className="flex gap-3 items-start max-w-[85%] self-end ml-auto flex-row-reverse">
                            <div className="h-7 w-7 rounded-full bg-orange-100 flex items-center justify-center font-bold text-orange-600 text-[10px] shrink-0 border border-orange-200">
                              AI
                            </div>
                            <div className="flex flex-col gap-1 items-end">
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">FPT Bot</span>
                              <div className="p-3 bg-orange-600 text-white rounded-2xl rounded-tr-none text-sm leading-relaxed font-medium shadow-xs">
                                {log.answer}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Pagination controls */}
          {chatLogs.length > 0 && (
            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
              <span className="text-xs font-semibold text-slate-500 bg-slate-50 border px-3 py-1.5 rounded-lg">
                Tổng số log: {totalLogs} | Trang {page}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  disabled={page <= 1 || isLogsLoading}
                  onClick={() => handlePageChange(page - 1)}
                  variant="ghost"
                  className="border text-slate-600 text-xs font-semibold px-3 py-1.5 h-8 disabled:opacity-50"
                >
                  Trang trước
                </Button>
                <Button
                  disabled={!hasNextLogs || isLogsLoading}
                  onClick={() => handlePageChange(page + 1)}
                  variant="ghost"
                  className="border text-slate-600 text-xs font-semibold px-3 py-1.5 h-8 disabled:opacity-50"
                >
                  Trang sau
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Role Change Confirmation Modal */}
      {showRoleModal && roleChangeUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white rounded-xl border shadow-lg max-w-md w-full p-6 space-y-4 animate-in zoom-in-95 duration-200 text-left">
            <h3 className="text-lg font-bold text-slate-900 border-b pb-2">Xác nhận thay đổi phân quyền</h3>
            
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-slate-400 font-semibold block text-xs uppercase">Người dùng</span>
                <span className="font-semibold text-slate-800">{roleChangeUser.username}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block text-xs uppercase">Email</span>
                <span className="font-medium text-slate-700">{roleChangeUser.email}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 bg-slate-50 p-2.5 rounded-lg border">
                <div>
                  <span className="text-slate-400 font-semibold block text-xxs uppercase">Từ</span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xxs font-bold bg-slate-100 text-slate-700 mt-1 capitalize animate-none">
                    {roleChangeUser.role}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 font-semibold block text-xxs uppercase">Thành</span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xxs font-bold bg-orange-100 text-orange-700 mt-1 capitalize animate-none">
                    {pendingRole}
                  </span>
                </div>
              </div>
              <p className="text-slate-600 font-semibold pt-1">Bạn có chắc muốn thực hiện thay đổi này?</p>
            </div>
            
            <div className="flex items-center justify-end gap-2 pt-2">
              <Button 
                variant="ghost" 
                onClick={() => { setShowRoleModal(false); setRoleChangeUser(null); setPendingRole(""); }}
                className="text-xs font-semibold text-slate-600 border bg-white hover:bg-slate-50"
              >
                Hủy
              </Button>
              <Button 
                onClick={confirmRoleChange}
                className="bg-orange-600 hover:bg-orange-700 text-white text-xs font-semibold"
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
