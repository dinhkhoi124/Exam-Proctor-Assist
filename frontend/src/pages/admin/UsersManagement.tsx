import { useEffect, useState, useRef } from "react";
import { api, getAdminWebSocketUrl } from "@/lib/api";
import { getApiErrorMessage } from "@/lib/api-errors";
import { Clock, Search, UserCheck, ChevronDown, ChevronUp, Trash2, Lock, Unlock, RotateCcw, AlertTriangle } from "lucide-react";
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
  is_deleted: boolean;
  deleted_at: string | null;
  purged_at: string | null;
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
  session_id?: string | null;
}

interface SessionLogItem {
  id: string;
  question: string;
  answer: string | null;
  topic: string;
  created_at: string;
}

interface ChatSessionDetailResponse {
  session_id: string;
  session_title: string;
  items: SessionLogItem[];
}

interface ChatLogsResponse {
  items: ChatLogItem[];
  page: number;
  limit: number;
  total: number;
  has_next: boolean;
}

interface TrashUserItem {
  id: string;
  username: string;
  email: string;
  role: string;
  delete_reason: string | null;
  deleted_at: string | null;
  deleted_by: string | null;
  deletion_source: "self_service" | "admin" | "unknown";
  owner_user_id: string | null;
  owner_username: string | null;
  owner_email: string;
  expires_at: string | null;
}

interface TrashChatBatch {
  batch_id: string;
  title: string;
  log_count: number;
  session_count: number;
  deleted_at: string | null;
  deleted_by: string | null;
  expires_at: string | null;
}

interface TrashResponse {
  users: TrashUserItem[];
  chat_batches: TrashChatBatch[];
}

export default function UsersManagement() {
  const [activeTab, setActiveTab] = useState<"users" | "logs" | "trash">("users");
  
  // Data lists
  const [users, setUsers] = useState<UserItem[]>([]);
  const [chatLogs, setChatLogs] = useState<ChatLogItem[]>([]);
  const [trash, setTrash] = useState<TrashResponse>({ users: [], chat_batches: [] });
  
  // Loaders
  const [isUsersLoading, setIsUsersLoading] = useState(true);
  const [isLogsLoading, setIsLogsLoading] = useState(false);
  const [isTrashLoading, setIsTrashLoading] = useState(false);
  
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
  const [sessionDetails, setSessionDetails] = useState<Record<string, SessionLogItem[]>>({});
  const [loadingSessionIds, setLoadingSessionIds] = useState<Set<string>>(new Set());
  const [selectedLogIds, setSelectedLogIds] = useState<Set<string>>(new Set());
  const [isActionLoading, setIsActionLoading] = useState(false);

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

  const fetchTrash = async (silent: boolean = false) => {
    try {
      if (!silent) setIsTrashLoading(true);
      const res = await api.get<TrashResponse>("/api/v1/admin/trash");
      setTrash(res.data);
    } catch (err) {
      console.error("Failed to fetch trash", err);
      toast.error("Không thể tải thùng rác");
    } finally {
      if (!silent) setIsTrashLoading(false);
    }
  };

  const fetchTrashRef = useRef(fetchTrash);
  useEffect(() => {
    fetchTrashRef.current = fetchTrash;
  });
  useEffect(() => {
    fetchUsersRef.current = fetchUsers;
  });

  const formatVietnamDateTime = (dateStr: string | null, includeTime = true) => {
    if (!dateStr) return "Chưa hoạt động";
    try {
      return new Intl.DateTimeFormat("vi-VN", {
        timeZone: "Asia/Ho_Chi_Minh",
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        ...(includeTime ? { hour: "2-digit", minute: "2-digit" } : {}),
      }).format(new Date(dateStr));
    } catch {
      return "Chưa hoạt động";
    }
  };

  const formatLastActive = (dateStr: string | null) => formatVietnamDateTime(dateStr);

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
    } catch (err) {
      console.error("Failed to update user role", err);
      toast.error(getApiErrorMessage(err, "Không thể cập nhật phân quyền"));
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
      if (!silent) {
        setSessionDetails({});
        setExpandedLogId(null);
      }
      setSelectedLogIds(new Set());
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
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Không thể thay đổi vai trò"));
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // Reset page and collapse expanded log on filter change
  const handleFilterChange = <T,>(setter: (value: T) => void, value: T) => {
    setter(value);
    setPage(1);
    setExpandedLogId(null);
    setSelectedLogIds(new Set());
  };

  // Trigger loading when activeTab, dropdown filters or page changes
  useEffect(() => {
    if (activeTab === "logs") {
      fetchChatLogsRef.current();
    } else if (activeTab === "trash") {
      fetchTrashRef.current();
    }
  }, [activeTab, userFilter, topicFilter, timeFilter, sortOrder, page]);

  // WebSocket Integration for real-time updates
  const fetchLogsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    const connectWs = () => {
      ws = new WebSocket(getAdminWebSocketUrl());

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Refresh on stats updates or when a new chat log is created
          if (data.type === "CHAT_LOG_CREATED" || data.type === "STATS_UPDATED") {
            if (!fetchLogsTimeoutRef.current) {
              fetchLogsTimeoutRef.current = setTimeout(() => {
                if (activeTab === "logs") {
                  fetchChatLogsRef.current(true);
                } else if (activeTab === "trash") {
                  fetchTrashRef.current(true);
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
    setSelectedLogIds(new Set());
  };



  const handleToggleLogDetails = async (log: ChatLogItem) => {
    if (expandedLogId === log.id) {
      setExpandedLogId(null);
      if (log.session_id) {
        setSessionDetails(previous => {
          const next = { ...previous };
          delete next[log.session_id!];
          return next;
        });
      }
      return;
    }

    setExpandedLogId(log.id);
    if (!log.session_id || sessionDetails[log.session_id]) return;

    try {
      setLoadingSessionIds(previous => new Set(previous).add(log.session_id!));
      const response = await api.get<ChatSessionDetailResponse>(
        `/api/v1/admin/chat-sessions/${log.session_id}/logs`,
      );
      setSessionDetails(previous => ({
        ...previous,
        [log.session_id!]: response.data.items,
      }));
    } catch (err) {
      setExpandedLogId(null);
      toast.error(getApiErrorMessage(err, "Không thể tải đầy đủ phiên chat"));
    } finally {
      setLoadingSessionIds(previous => {
        const next = new Set(previous);
        if (log.session_id) next.delete(log.session_id);
        return next;
      });
    }
  };
  const toggleLogSelection = (logId: string) => {
    setSelectedLogIds(previous => {
      const next = new Set(previous);
      if (next.has(logId)) next.delete(logId);
      else next.add(logId);
      return next;
    });
  };

  const toggleCurrentPageSelection = () => {
    const allSelected = chatLogs.length > 0 && chatLogs.every(log => selectedLogIds.has(log.id));
    setSelectedLogIds(allSelected ? new Set() : new Set(chatLogs.map(log => log.id)));
  };

  const confirmAndDeleteLogs = async (payload: Record<string, unknown>) => {
    try {
      setIsActionLoading(true);
      const preview = await api.post<{ log_count: number; session_count: number }>(
        "/api/v1/admin/chat-logs/delete-preview",
        payload,
      );
      if (preview.data.log_count === 0) {
        toast.info("Không có nhật ký phù hợp để xóa");
        return;
      }
      const confirmed = window.confirm(
        `Xóa ${preview.data.log_count} nhật ký thuộc ${preview.data.session_count} phiên chat? Dữ liệu sẽ được xóa mềm.`,
      );
      if (!confirmed) return;

      const result = await api.post<{ deleted_logs: number; deleted_sessions: number }>(
        "/api/v1/admin/chat-logs/bulk-delete",
        payload,
      );
      toast.success(`Đã xóa ${result.data.deleted_logs} nhật ký`);
      setSelectedLogIds(new Set());
      setExpandedLogId(null);
      if (page > 1 && result.data.deleted_logs >= chatLogs.length) setPage(page - 1);
      else fetchChatLogs(true);
      fetchUsers(true);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Không thể xóa nhật ký"));
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleDeleteSelectedLogs = () => {
    if (selectedLogIds.size === 0) return;
    confirmAndDeleteLogs({ mode: "selected", log_ids: Array.from(selectedLogIds) });
  };

  const handleDeleteSession = (sessionId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    confirmAndDeleteLogs({ mode: "session", session_ids: [sessionId] });
  };

  const handleDeleteByRange = () => {
    if (userFilter === "all" || timeFilter === "all") {
      toast.error("Hãy chọn một người dùng và một mốc thời gian trước khi xóa");
      return;
    }
    confirmAndDeleteLogs({ mode: "range", user_id: userFilter, range: timeFilter });
  };

  const handleAccountStatus = async (user: UserItem) => {
    const nextActive = !user.is_active;
    if (!window.confirm(`${nextActive ? "Mở khóa" : "Khóa"} tài khoản ${user.username}?`)) return;
    try {
      setIsActionLoading(true);
      await api.patch(`/api/v1/admin/users/${user.id}/status`, { is_active: nextActive });
      toast.success(nextActive ? "Đã mở khóa tài khoản" : "Đã khóa tài khoản");
      fetchUsers(true);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Không thể cập nhật trạng thái tài khoản"));
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleDeleteUser = async (user: UserItem) => {
    if (!window.confirm(`Xóa tài khoản ${user.username}? Tài khoản có thể được khôi phục trong 30 ngày.`)) return;
    try {
      setIsActionLoading(true);
      await api.delete(`/api/v1/admin/users/${user.id}`);
      toast.success("Tài khoản đã chuyển sang trạng thái chờ xóa");
      fetchUsers(true);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Không thể xóa tài khoản"));
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleRestoreUser = async (user: Pick<UserItem, "id" | "username">) => {
    if (!window.confirm(`Khôi phục tài khoản ${user.username}?`)) return;
    try {
      setIsActionLoading(true);
      await api.post(`/api/v1/admin/users/${user.id}/restore`);
      toast.success("Đã khôi phục tài khoản");
      fetchUsers(true);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Không thể khôi phục tài khoản"));
    } finally {
      setIsActionLoading(false);
    }
  };
  // Filter user list for table search
  const requestPermanentConfirmation = () => window.prompt(
    'Thao tác này không thể hoàn tác. Nhập chính xác "XOA VINH VIEN" để tiếp tục:',
  );

  const handleRestoreTrashUser = async (user: TrashUserItem) => {
    if (!window.confirm(`Khôi phục tài khoản ${user.username}?`)) return;
    try {
      setIsActionLoading(true);
      await api.post(`/api/v1/admin/users/${user.id}/restore`);
      toast.success("Đã khôi phục tài khoản");
      await Promise.all([fetchTrash(true), fetchUsers(true)]);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Không thể khôi phục tài khoản"));
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleRestoreChatBatch = async (batch: TrashChatBatch) => {
    if (!window.confirm(`Khôi phục mục trò chuyện “${batch.title}”?`)) return;
    try {
      setIsActionLoading(true);
      await api.post(`/api/v1/admin/trash/chats/${batch.batch_id}/restore`);
      toast.success("Đã khôi phục dữ liệu trò chuyện");
      await Promise.all([fetchTrash(true), fetchUsers(true)]);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Không thể khôi phục dữ liệu trò chuyện"));
    } finally {
      setIsActionLoading(false);
    }
  };

  const handlePermanentDeleteChatBatch = async (batch: TrashChatBatch) => {
    const confirmation = requestPermanentConfirmation();
    if (confirmation === null) return;
    try {
      setIsActionLoading(true);
      await api.delete(`/api/v1/admin/trash/chats/${batch.batch_id}`, {
        params: { confirmation },
      });
      toast.success("Đã xóa vĩnh viễn dữ liệu trò chuyện");
      await fetchTrash(true);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Không thể xóa vĩnh viễn dữ liệu trò chuyện"));
    } finally {
      setIsActionLoading(false);
    }
  };

  const handlePermanentDeleteUser = async (user: TrashUserItem) => {
    const confirmation = requestPermanentConfirmation();
    if (confirmation === null) return;
    try {
      setIsActionLoading(true);
      await api.delete(`/api/v1/admin/trash/users/${user.id}`, {
        params: { confirmation },
      });
      toast.success("Đã xóa vĩnh viễn thông tin cá nhân của tài khoản");
      await Promise.all([fetchTrash(true), fetchUsers(true)]);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Không thể xóa vĩnh viễn tài khoản"));
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleEmptyTrash = async () => {
    const confirmation = requestPermanentConfirmation();
    if (confirmation === null) return;
    try {
      setIsActionLoading(true);
      await api.delete("/api/v1/admin/trash", {
        data: { scope: "all", confirmation },
      });
      toast.success("Đã dọn sạch thùng rác");
      await Promise.all([fetchTrash(true), fetchUsers(true)]);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Không thể dọn thùng rác"));
    } finally {
      setIsActionLoading(false);
    }
  };

  const filteredUsersList = users.filter(u =>
    !u.is_deleted && (
      u.username.toLowerCase().includes(searchSearch.toLowerCase()) ||
      u.email.toLowerCase().includes(searchSearch.toLowerCase())
    )
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Quản lý người dùng</h1>
        <p className="text-slate-500 mt-1">Phân quyền, thăng cấp/hạ cấp người dùng và xem nhật ký hoạt động.</p>
      </div>

      {/* TABS CONTAINER */}
      <div className="flex overflow-x-auto border-b border-slate-200">
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
        <button
          onClick={() => setActiveTab("trash")}
          className={`px-5 py-3 font-semibold text-sm transition-all border-b-2 -mb-[2px] flex items-center gap-2 ${
            activeTab === "trash"
              ? "border-orange-600 text-orange-600"
              : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          <Trash2 className="h-4 w-4" />
          Thùng rác
        </button>
      </div>

      {/* USER LIST TAB */}
      {activeTab === "users" && (
        <div className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative w-full sm:w-72">
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
              <table className="min-w-[1250px] w-full text-sm text-left">
                <thead className="bg-slate-50 text-slate-500 border-b">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Họ tên</th>
                    <th className="px-6 py-4 font-semibold">Email</th>
                    <th className="px-6 py-4 font-semibold">Vai trò</th>
                    <th className="px-6 py-4 font-semibold text-center">Câu hỏi</th>
                    <th className="px-6 py-4 font-semibold">Tạo lúc</th>
                    <th className="px-6 py-4 font-semibold">Hoạt động cuối</th>
                    <th className="px-6 py-4 font-semibold text-right">Thay đổi vai trò</th>
                    <th className="px-6 py-4 font-semibold">Trạng thái</th>
                    <th className="px-6 py-4 font-semibold text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {isUsersLoading ? (
                    <tr>
                      <td colSpan={9} className="px-6 py-8 text-center text-slate-400 animate-pulse">
                        Đang tải danh sách người dùng...
                      </td>
                    </tr>
                  ) : filteredUsersList.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-6 py-8 text-center text-slate-400">
                        Không tìm thấy người dùng phù hợp.
                      </td>
                    </tr>
                  ) : (
                    filteredUsersList.map((u) => (
                      <tr key={u.id} className={`hover:bg-slate-50/50 transition-colors ${u.is_deleted ? "opacity-70" : ""}`}>
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
                          {formatVietnamDateTime(u.created_at, false)}
                        </td>
                        <td className="px-6 py-4 text-slate-400 text-xs">
                          {formatLastActive(u.last_active)}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <select
                            value={u.role}
                            onChange={(e) => handleSelectRoleChange(u, e.target.value)}
                            className="text-xs bg-white border rounded px-2 py-1 text-slate-700 font-medium hover:border-slate-300 focus:outline-none focus:ring-1 focus:ring-orange-500"
                            disabled={u.is_deleted || isActionLoading}
                          >
                            <option value="user">User</option>
                            <option value="manager">Management</option>
                            <option value="admin">Admin</option>
                          </select>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xxs font-bold ${
                            u.is_deleted
                              ? "bg-red-100 text-red-700"
                              : u.is_active
                                ? "bg-emerald-100 text-emerald-700"
                                : "bg-amber-100 text-amber-700"
                          }`}>
                            {u.is_deleted ? "Chờ xóa" : u.is_active ? "Đang hoạt động" : "Đã khóa"}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex justify-end gap-1.5">
                            {u.is_deleted ? (
                              <Button disabled={isActionLoading} variant="ghost" className="h-8 px-2 text-xs text-emerald-700" onClick={() => handleRestoreUser(u)}>
                                <RotateCcw className="mr-1 h-3.5 w-3.5" /> Khôi phục
                              </Button>
                            ) : (
                              <>
                                <Button disabled={isActionLoading} variant="ghost" className="h-8 px-2 text-xs text-slate-700" onClick={() => handleAccountStatus(u)}>
                                  {u.is_active ? <Lock className="mr-1 h-3.5 w-3.5" /> : <Unlock className="mr-1 h-3.5 w-3.5" />}
                                  {u.is_active ? "Khóa" : "Mở khóa"}
                                </Button>
                                <Button disabled={isActionLoading} variant="ghost" className="h-8 px-2 text-xs text-red-600" onClick={() => handleDeleteUser(u)}>
                                  <Trash2 className="mr-1 h-3.5 w-3.5" /> Xóa
                                </Button>
                              </>
                            )}
                          </div>
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
                {users.filter(u => !u.is_deleted).map(u => (
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
                <option value="week">Tuần này</option>
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
          {chatLogs.length > 0 && (
            <div className="flex flex-col gap-3 rounded-xl border bg-white p-3 shadow-sm sm:flex-row sm:items-center sm:justify-between">
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-600">
                <input
                  type="checkbox"
                  checked={chatLogs.every(log => selectedLogIds.has(log.id))}
                  onChange={toggleCurrentPageSelection}
                  className="h-4 w-4 accent-orange-600"
                />
                Chọn {chatLogs.length} mục trên trang này
              </label>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-slate-500">Đã chọn: {selectedLogIds.size}</span>
                <Button
                  type="button"
                  variant="ghost"
                  disabled={selectedLogIds.size === 0 || isActionLoading}
                  onClick={handleDeleteSelectedLogs}
                  className="h-8 border px-3 text-xs font-semibold text-red-600"
                >
                  <Trash2 className="mr-1 h-3.5 w-3.5" /> Xóa mục đã chọn
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  disabled={userFilter === "all" || timeFilter === "all" || isActionLoading}
                  onClick={handleDeleteByRange}
                  className="h-8 border px-3 text-xs font-semibold text-red-600"
                >
                  <Trash2 className="mr-1 h-3.5 w-3.5" /> Xóa theo tài khoản và thời gian
                </Button>
              </div>
            </div>
          )}


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
                  
                  const detailItems: SessionLogItem[] = log.session_id
                    ? sessionDetails[log.session_id] ?? []
                    : [{
                        id: log.id,
                        question: log.question,
                        answer: log.answer,
                        topic: log.topic,
                        created_at: log.created_at,
                      }];
                  const isDetailLoading = Boolean(
                    log.session_id && loadingSessionIds.has(log.session_id),
                  );
                  const questionPreview = log.question.length > 80 
                    ? log.question.slice(0, 80) + "..." 
                    : log.question;
                    
                  return (
                    <div key={log.id} className="bg-white rounded-xl border shadow-sm overflow-hidden flex flex-col transition-all duration-205">
                      {/* Summary Row */}
                      <div 
                        onClick={() => void handleToggleLogDetails(log)}
                        className="px-4 py-3.5 sm:px-5 flex items-center justify-between cursor-pointer hover:bg-slate-50/70 transition-colors select-none flex-wrap gap-3 sm:gap-4 text-xs"
                      >
                        <div className="flex items-center gap-2.5 min-w-[180px]">
                          <input
                            type="checkbox"
                            checked={selectedLogIds.has(log.id)}
                            onClick={(event) => event.stopPropagation()}
                            onChange={() => toggleLogSelection(log.id)}
                            className="h-4 w-4 shrink-0 accent-orange-600"
                          />
                          <div className="h-6 w-6 rounded-full bg-orange-100 flex items-center justify-center font-bold text-orange-600 text-xxs">
                            {log.username.slice(0, 2).toUpperCase()}
                          </div>
                          <div className="flex flex-col">
                            <span className="font-bold text-slate-800">{log.username}</span>
                            <span className="text-[10px] text-slate-400 font-normal">{log.email}</span>
                          </div>
                        </div>

                        {/* Session & Question Preview */}
                        <div className="w-full min-w-0 px-0 text-slate-500 font-medium sm:flex-1 sm:min-w-[240px] sm:px-2 sm:truncate">
                          <span className="text-slate-800 font-semibold mr-1.5">{sessionName}</span>
                          <span className="italic text-xs font-normal">"{questionPreview}"</span>
                        </div>

                        {/* Badges & Actions */}
                        <div className="flex w-full flex-wrap items-center gap-2 font-medium sm:ml-auto sm:w-auto sm:shrink-0 sm:gap-3">
                          <span className="px-2 py-0.5 bg-orange-50 text-orange-700 font-bold rounded text-[10px] uppercase tracking-wider">
                            {log.topic || "General Guidance"}
                          </span>
                          <span className="flex items-center gap-1 text-slate-400">
                            <Clock className="h-3 w-3" />
                            {formatVietnamDateTime(log.created_at)}
                          </span>
                          <button className="text-orange-600 hover:text-orange-700 font-bold flex items-center gap-1 pl-1">
                            {isExpanded ? "Thu gọn" : "Xem chi tiết"}
                            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                          </button>
                          {log.session_id && (
                            <button
                              type="button"
                              disabled={isActionLoading}
                              onClick={(event) => handleDeleteSession(log.session_id!, event)}
                              className="flex items-center gap-1 text-red-600 hover:text-red-700 disabled:opacity-50"
                            >
                              <Trash2 className="h-3.5 w-3.5" /> Xóa phiên
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Expanded Content Accordion */}
                      {isExpanded && (
                        <div className="space-y-5 border-t bg-slate-50/20 px-4 pb-6 pt-4 animate-in slide-in-from-top-2 duration-200 sm:px-6">
                          {isDetailLoading ? (
                            <div className="py-8 text-center text-sm font-medium text-slate-400 animate-pulse">
                              Đang tải đầy đủ phiên chat...
                            </div>
                          ) : detailItems.length === 0 ? (
                            <div className="py-8 text-center text-sm text-slate-400">
                              Phiên chat này chưa có nội dung đang hoạt động.
                            </div>
                          ) : (
                            <>
                              <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3 text-xs">
                                <span className="font-bold text-slate-700">
                                  {log.session_id ? `Toàn bộ phiên chat · ${detailItems.length} lượt` : "Chi tiết lượt chat"}
                                </span>
                                <span className="text-slate-400">Sắp xếp từ cũ đến mới</span>
                              </div>
                              {detailItems.map((item, index) => (
                                <div key={item.id} className="space-y-4 rounded-xl border bg-white p-4 shadow-xs">
                                  <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                                    <span>Lượt {index + 1}</span>
                                    <span>{item.topic || "General Guidance"} · {formatVietnamDateTime(item.created_at)}</span>
                                  </div>

                                  <div className="flex max-w-full items-start gap-3 sm:max-w-[85%]">
                                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border bg-slate-100 text-[10px] font-bold text-slate-500">
                                      US
                                    </div>
                                    <div className="flex flex-col gap-1">
                                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Giám thị</span>
                                      <div className="rounded-2xl rounded-tl-none bg-slate-100 p-3 text-sm font-medium leading-relaxed text-slate-800 shadow-xs">
                                        {item.question}
                                      </div>
                                    </div>
                                  </div>

                                  <div className="ml-auto flex max-w-full flex-row-reverse items-start gap-3 sm:max-w-[85%]">
                                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-orange-200 bg-orange-100 text-[10px] font-bold text-orange-600">
                                      AI
                                    </div>
                                    <div className="flex flex-col items-end gap-1">
                                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">FPT Bot</span>
                                      <div className="rounded-2xl rounded-tr-none bg-orange-600 p-3 text-sm font-medium leading-relaxed text-white shadow-xs">
                                        {item.answer || "Không có câu trả lời được lưu."}
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </>
                          )}
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
            <div className="flex flex-col gap-3 border-t border-slate-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
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


      {/* TRASH TAB */}
      {activeTab === "trash" && (
        <div className="space-y-6">
          <div className="flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3 text-amber-900">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
              <div>
                <p className="text-sm font-bold">Dữ liệu trong thùng rác được giữ tối đa 30 ngày</p>
                <p className="mt-1 text-xs text-amber-700">Sau thời hạn này, dữ liệu trò chuyện sẽ bị xóa cứng; thông tin cá nhân của tài khoản sẽ được ẩn danh tự động.</p>
              </div>
            </div>
            <Button
              type="button"
              disabled={isActionLoading || (trash.users.length === 0 && trash.chat_batches.length === 0)}
              onClick={handleEmptyTrash}
              className="shrink-0 bg-red-600 text-white hover:bg-red-700"
            >
              <Trash2 className="mr-2 h-4 w-4" /> Dọn sạch thùng rác
            </Button>
          </div>

          {isTrashLoading ? (
            <div className="rounded-xl border bg-white p-10 text-center text-slate-400 animate-pulse">Đang tải thùng rác...</div>
          ) : (
            <>
              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="font-bold text-slate-900">Nhật ký và phiên chat đã xóa</h2>
                  <span className="text-xs font-medium text-slate-500">
                    {trash.chat_batches.length} đợt xóa · {trash.chat_batches.filter(batch => batch.deletion_source === "self_service").length} do người dùng tự xóa
                  </span>
                </div>
                {trash.chat_batches.length === 0 ? (
                  <div className="rounded-xl border bg-white p-8 text-center text-sm text-slate-400">Không có dữ liệu trò chuyện trong thùng rác.</div>
                ) : (
                  <div className="space-y-3">
                    {trash.chat_batches.map((batch) => (
                      <div key={batch.batch_id} className="flex flex-col gap-4 rounded-xl border bg-white p-4 shadow-sm lg:flex-row lg:items-center lg:justify-between">
                        <div className="min-w-0 space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="truncate text-sm font-bold text-slate-900">{batch.title}</p>
                            <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold ${
                              batch.deletion_source === "self_service"
                                ? "bg-violet-100 text-violet-700"
                                : batch.deletion_source === "admin"
                                  ? "bg-red-100 text-red-700"
                                  : "bg-slate-100 text-slate-600"
                            }`}>
                              {batch.deletion_source === "self_service"
                                ? "Người dùng tự xóa"
                                : batch.deletion_source === "admin"
                                  ? "Admin xóa"
                                  : "Không xác định nguồn"}
                            </span>
                          </div>
                          <p className="text-xs text-slate-500">{batch.log_count} nhật ký · {batch.session_count} phiên chat</p>
                          <p className="text-xs text-slate-500">
                            Chủ phiên: <span className="font-semibold text-slate-700">{batch.owner_username || "Không xác định"}</span>
                            {batch.owner_email ? ` · ${batch.owner_email}` : ""}
                          </p>
                          <p className="text-xs text-slate-400">
                            Xóa lúc {formatVietnamDateTime(batch.deleted_at)}{batch.deleted_by ? ` bởi ${batch.deleted_by}` : ""}
                          </p>
                          <p className="text-xs font-medium text-red-500">Tự xóa sau: {formatVietnamDateTime(batch.expires_at)}</p>
                        </div>
                        <div className="flex shrink-0 flex-wrap gap-2">
                          <Button type="button" variant="ghost" disabled={isActionLoading} onClick={() => handleRestoreChatBatch(batch)} className="border text-xs text-emerald-700">
                            <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> Khôi phục
                          </Button>
                          <Button type="button" variant="ghost" disabled={isActionLoading} onClick={() => handlePermanentDeleteChatBatch(batch)} className="border text-xs text-red-600">
                            <Trash2 className="mr-1.5 h-3.5 w-3.5" /> Xóa vĩnh viễn
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="font-bold text-slate-900">Tài khoản đã xóa</h2>
                  <span className="text-xs font-medium text-slate-500">{trash.users.length} tài khoản</span>
                </div>
                {trash.users.length === 0 ? (
                  <div className="rounded-xl border bg-white p-8 text-center text-sm text-slate-400">Không có tài khoản trong thùng rác.</div>
                ) : (
                  <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
                    <div className="divide-y">
                      {trash.users.map((user) => (
                        <div key={user.id} className="flex flex-col gap-4 p-4 lg:flex-row lg:items-center lg:justify-between">
                          <div className="min-w-0 space-y-1">
                            <p className="truncate text-sm font-bold text-slate-900">{user.username} <span className="ml-2 text-xs font-medium text-slate-400">{user.role}</span></p>
                            <p className="truncate text-xs text-slate-500">{user.email}</p>
                            <p className="text-xs text-slate-400">
                              Xóa lúc {formatVietnamDateTime(user.deleted_at)}{user.deleted_by ? ` bởi ${user.deleted_by}` : ""}
                            </p>
                            {user.delete_reason && <p className="text-xs text-slate-500">Lý do: {user.delete_reason}</p>}
                            <p className="text-xs font-medium text-red-500">Ẩn danh sau: {formatVietnamDateTime(user.expires_at)}</p>
                          </div>
                          <div className="flex shrink-0 flex-wrap gap-2">
                            <Button type="button" variant="ghost" disabled={isActionLoading} onClick={() => handleRestoreTrashUser(user)} className="border text-xs text-emerald-700">
                              <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> Khôi phục
                            </Button>
                            <Button type="button" variant="ghost" disabled={isActionLoading} onClick={() => handlePermanentDeleteUser(user)} className="border text-xs text-red-600">
                              <Trash2 className="mr-1.5 h-3.5 w-3.5" /> Xóa vĩnh viễn
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            </>
          )}
        </div>
      )}
      {/* Role Change Confirmation Modal */}
      {showRoleModal && roleChangeUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="max-h-[90dvh] w-full max-w-md overflow-y-auto rounded-xl border bg-white p-5 shadow-lg sm:p-6 space-y-4 animate-in zoom-in-95 duration-200 text-left">
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
