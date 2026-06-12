import { useState, useEffect, useRef } from "react";
import { 
  MessageSquare, AlertCircle, ThumbsUp, ThumbsDown, CheckCircle2, 
  Trash2, Search, ChevronDown, ChevronUp, RefreshCw, Clock, UserCheck
} from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { format } from "date-fns";
import { useAuth } from "@/context/AuthContext";

interface FeedbackUserDetail {
  username: string;
  email: string;
}

interface FeedbackChatDetail {
  question: string;
  answer?: string;
}

interface FeedbackItem {
  id: string;
  user_id: string | null;
  chat_id: string | null;
  rating: "like" | "dislike" | string;
  comment: string | null;
  is_resolved: boolean;
  is_deleted: boolean;
  created_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  user?: FeedbackUserDetail | null;
  chat_log?: FeedbackChatDetail | null;
  resolver?: FeedbackUserDetail | null;
}

export default function FeedbackManagement() {
  const { user } = useAuth();
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters states
  const [search, setSearch] = useState("");
  const [ratingFilter, setRatingFilter] = useState<"all" | "like" | "dislike">("all");
  const [resolvedFilter, setResolvedFilter] = useState<"all" | "resolved" | "unresolved">("all");

  // Expanded row IDs
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const fetchFeedbacks = async (silent: boolean = false) => {
    if (!silent) {
      setIsLoading(true);
    }
    try {
      let url = "/api/v1/admin/feedbacks?";
      
      const params = new URLSearchParams();
      if (search.trim()) {
        params.append("search", search);
      }
      if (ratingFilter !== "all") {
        params.append("rating", ratingFilter);
      }
      if (resolvedFilter !== "all") {
        params.append("is_resolved", resolvedFilter === "resolved" ? "true" : "false");
      }
      
      url += params.toString();
      const res = await api.get<FeedbackItem[]>(url);
      setFeedbacks(res.data);
      setError(null);
    } catch (err: any) {
      console.error("Failed to load feedbacks", err);
      setError("Không thể tải danh sách phản hồi. Vui lòng thử lại.");
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  };

  // Keep a reference to fetchFeedbacks to avoid stale closures in WebSocket useEffect
  const fetchFeedbacksRef = useRef(fetchFeedbacks);
  useEffect(() => {
    fetchFeedbacksRef.current = fetchFeedbacks;
  });

  useEffect(() => {
    fetchFeedbacks();
  }, [ratingFilter, resolvedFilter]); // immediate load on drop downs

  // WebSocket Integration for real-time updates
  const fetchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
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
          if (data.type === "STATS_UPDATED") {
            if (!fetchTimeoutRef.current) {
              fetchTimeoutRef.current = setTimeout(() => {
                fetchFeedbacksRef.current(true);
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
  }, []);

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      fetchFeedbacks();
    }
  };

  const toggleRow = (id: string) => {
    const next = new Set(expandedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setExpandedIds(next);
  };

  const handleToggleResolve = async (feedback: FeedbackItem, e: React.MouseEvent) => {
    e.stopPropagation(); // Stop row expansion
    const newStatus = !feedback.is_resolved;
    
    // Save current feedbacks for rollback
    const previousFeedbacks = feedbacks;
    
    // Optimistic Update
    setFeedbacks(prevFeedbacks =>
      prevFeedbacks.map(fb => {
        if (fb.id === feedback.id) {
          return {
            ...fb,
            is_resolved: newStatus,
            resolved_at: newStatus ? new Date().toISOString() : null,
            resolved_by: newStatus ? (user?.id ? String(user.id) : "Quản trị viên") : null,
            resolver: newStatus ? {
              username: user?.username || "Quản trị viên",
              email: user?.email || ""
            } : null
          };
        }
        return fb;
      })
    );

    try {
      await api.put(`/api/v1/admin/feedbacks/${feedback.id}/resolve`, {
        is_resolved: newStatus
      });
      toast.success(newStatus ? "Đã đánh dấu xử lý phản hồi" : "Đã hủy đánh dấu xử lý");
      // Silently sync from backend to get the exact record
      fetchFeedbacks(true);
    } catch (err) {
      console.error("Failed to update resolve status", err);
      toast.error("Không thể cập nhật trạng thái phản hồi");
      // Rollback to previous state
      setFeedbacks(previousFeedbacks);
    }
  };

  const handleDeleteFeedback = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Stop row expansion
    if (!confirm("Bạn có chắc chắn muốn xóa phản hồi này?")) return;

    // Save current feedbacks for rollback
    const previousFeedbacks = feedbacks;

    // Optimistic Update
    setFeedbacks(prevFeedbacks => prevFeedbacks.filter(fb => fb.id !== id));

    try {
      await api.delete(`/api/v1/admin/feedbacks/${id}`);
      toast.success("Đã xóa phản hồi thành công");
      // Silently sync from backend
      fetchFeedbacks(true);
    } catch (err) {
      console.error("Failed to delete feedback", err);
      toast.error("Không thể xóa phản hồi");
      // Rollback to previous state
      setFeedbacks(previousFeedbacks);
    }
  };

  const formatDateTime = (dateStr: string) => {
    try {
      return format(new Date(dateStr), "dd/MM/yyyy HH:mm");
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Phản hồi người dùng</h1>
          <p className="text-slate-500 mt-1">Xem và xử lý ý kiến đóng góp, mức độ hài lòng từ Giám thị (Proctor) đối với chatbot.</p>
        </div>
        <button
          onClick={() => fetchFeedbacks()}
          disabled={isLoading}
          className="self-start sm:self-center p-2 rounded-lg border hover:bg-slate-50 text-slate-600 disabled:opacity-50 flex items-center gap-1.5 text-xs font-semibold bg-white"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          Tải lại
        </button>
      </div>

      {/* FILTER BAR */}
      <div className="bg-white rounded-xl border shadow-sm p-4 grid gap-4 md:grid-cols-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Tìm theo comment, email, Q&A..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm bg-white text-slate-750 focus:outline-none focus:ring-1 focus:ring-orange-500"
          />
          {search && (
            <span className="absolute right-3 top-3 text-[10px] text-slate-400 font-semibold cursor-pointer" onClick={() => { setSearch(""); fetchFeedbacks(); }}>
              Xóa
            </span>
          )}
        </div>

        {/* Rating Filter */}
        <div className="flex flex-col gap-1">
          <select
            value={ratingFilter}
            onChange={(e: any) => setRatingFilter(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg text-sm bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-orange-500"
          >
            <option value="all">Tất cả đánh giá</option>
            <option value="like">Thích (Like)</option>
            <option value="dislike">Không thích (Dislike)</option>
          </select>
        </div>

        {/* Resolve Filter */}
        <div className="flex flex-col gap-1">
          <select
            value={resolvedFilter}
            onChange={(e: any) => setResolvedFilter(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg text-sm bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-orange-500"
          >
            <option value="all">Tất cả trạng thái xử lý</option>
            <option value="unresolved">Chưa xử lý (Unresolved)</option>
            <option value="resolved">Đã xử lý (Resolved)</option>
          </select>
        </div>

        {/* Search Submit button */}
        <button
          onClick={() => fetchFeedbacks()}
          className="w-full py-2 bg-orange-600 hover:bg-orange-750 text-white rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-1.5"
        >
          <Search className="h-4 w-4" />
          Áp dụng bộ lọc
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2 border border-red-100 font-medium">
          <AlertCircle className="h-5 w-5" />
          {error}
        </div>
      )}

      {/* FEEDBACK LIST TABLE */}
      {isLoading ? (
        <div className="bg-white rounded-xl border shadow-sm p-12 text-center text-slate-400 animate-pulse font-medium">
          Đang tải danh sách phản hồi...
        </div>
      ) : feedbacks.length === 0 ? (
        <div className="bg-white rounded-xl border shadow-sm p-12 text-center">
          <div className="flex flex-col items-center justify-center max-w-md mx-auto space-y-3">
            <div className="h-12 w-12 rounded-full bg-slate-50 border flex items-center justify-center text-slate-400">
              <MessageSquare className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <h4 className="font-semibold text-slate-800 text-sm">Không tìm thấy phản hồi</h4>
              <p className="text-xs text-slate-400">
                Không có dữ liệu phản hồi nào trùng khớp với bộ lọc tìm kiếm hiện tại của bạn.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="bg-slate-50 border-b text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  <th className="px-6 py-3.5">Người gửi</th>
                  <th className="px-6 py-3.5 w-32">Đánh giá</th>
                  <th className="px-6 py-3.5">Ý kiến đóng góp (Comment)</th>
                  <th className="px-6 py-3.5 w-44">Ngày gửi</th>
                  <th className="px-6 py-3.5 w-36">Trạng thái</th>
                  <th className="px-6 py-3.5 w-24 text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y text-sm text-slate-700">
                {feedbacks.map((fb) => {
                  const isExpanded = expandedIds.has(fb.id);
                  const isLike = fb.rating === "like";
                  
                  return (
                    <>
                      <tr 
                        key={fb.id}
                        onClick={() => toggleRow(fb.id)}
                        className={`hover:bg-slate-50/70 transition-colors cursor-pointer select-none ${isExpanded ? "bg-slate-50/40" : ""}`}
                      >
                        {/* User */}
                        <td className="px-6 py-4">
                          {fb.user ? (
                            <div className="flex flex-col">
                              <span className="font-semibold text-slate-900">{fb.user.username}</span>
                              <span className="text-xxs text-slate-400">{fb.user.email}</span>
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">Người dùng đã xóa</span>
                          )}
                        </td>

                        {/* Rating */}
                        <td className="px-6 py-4">
                          {isLike ? (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 px-2.5 py-0.5 rounded-full border border-green-200">
                              <ThumbsUp className="h-3 w-3" />
                              Hài lòng
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-red-700 bg-red-50 px-2.5 py-0.5 rounded-full border border-red-200">
                              <ThumbsDown className="h-3 w-3" />
                              Góp ý
                            </span>
                          )}
                        </td>

                        {/* Comment */}
                        <td className="px-6 py-4">
                          {fb.comment ? (
                            <p className="line-clamp-2 max-w-md text-xs text-slate-650">
                              {fb.comment}
                            </p>
                          ) : (
                            <span className="text-slate-400 italic text-xs">Không có bình luận</span>
                          )}
                        </td>

                        {/* Date */}
                        <td className="px-6 py-4 text-xs text-slate-500">
                          {formatDateTime(fb.created_at)}
                        </td>

                        {/* Status */}
                        <td className="px-6 py-4">
                          {fb.is_resolved ? (
                            <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded">
                              ✓ Đã xử lý
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs font-semibold text-amber-800 bg-amber-100 px-2 py-0.5 rounded">
                              • Chưa xử lý
                            </span>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="px-6 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={(e) => handleToggleResolve(fb, e)}
                              className={`p-1.5 rounded-md border transition-colors ${
                                fb.is_resolved 
                                  ? "bg-slate-100 border-slate-200 text-slate-500 hover:bg-slate-200" 
                                  : "bg-orange-50 border-orange-200 text-orange-600 hover:bg-orange-100"
                              }`}
                              title={fb.is_resolved ? "Đánh dấu chưa xử lý" : "Đánh dấu đã xử lý"}
                            >
                              <CheckCircle2 className="h-4 w-4" />
                            </button>
                            <button
                              onClick={(e) => handleDeleteFeedback(fb.id, e)}
                              className="p-1.5 rounded-md border border-red-150 text-red-600 hover:bg-red-50 transition-colors"
                              title="Xóa phản hồi (Soft delete)"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                            <span className="text-slate-350 shrink-0 ml-1">
                              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                            </span>
                          </div>
                        </td>
                      </tr>

                      {/* EXPANDED CONTENT ACCORDION */}
                      {isExpanded && (
                        <tr key={`${fb.id}-expanded`} className="bg-slate-50/35 border-b">
                          <td colSpan={6} className="px-8 py-5">
                            <div className="grid gap-6 md:grid-cols-2">
                              {/* Left: Chat history logs */}
                              <div className="space-y-3 bg-white p-4 rounded-xl border border-slate-150 shadow-xs">
                                <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5 border-b pb-2">
                                  <MessageSquare className="h-4 w-4 text-orange-500" />
                                  Nội dung hội thoại liên quan
                                </h5>
                                
                                {fb.chat_log ? (
                                  <div className="space-y-4 text-xs">
                                    <div className="space-y-1">
                                      <span className="font-semibold text-slate-800 bg-slate-100 px-2 py-0.5 rounded">Giám thị hỏi:</span>
                                      <p className="pl-2 border-l-2 border-slate-200 py-1 text-slate-700 italic">
                                        "{fb.chat_log.question}"
                                      </p>
                                    </div>
                                    <div className="space-y-1">
                                      <span className="font-semibold text-slate-800 bg-orange-50 text-orange-800 px-2 py-0.5 rounded">AI trả lời:</span>
                                      <p className="pl-2 border-l-2 border-orange-200 py-1 text-slate-700 whitespace-pre-line">
                                        {fb.chat_log.answer || "Không có câu trả lời"}
                                      </p>
                                    </div>
                                  </div>
                                ) : (
                                  <p className="text-xs text-slate-400 italic">
                                    ⚠️ Chi tiết tin nhắn đã bị xóa khỏi hệ thống hoặc không tìm thấy.
                                  </p>
                                )}
                              </div>

                              {/* Right: Resolution Auditing logs */}
                              <div className="space-y-3 bg-white p-4 rounded-xl border border-slate-150 shadow-xs flex flex-col justify-between">
                                <div className="space-y-3">
                                  <h5 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5 border-b pb-2">
                                    <UserCheck className="h-4 w-4 text-orange-500" />
                                    Lịch sử xử lý quản trị
                                  </h5>

                                  <div className="space-y-3 text-xs">
                                    <div className="flex items-center gap-2">
                                      <Clock className="h-4 w-4 text-slate-400 shrink-0" />
                                      <span className="text-slate-500">Ngày gửi:</span>
                                      <span className="font-medium">{formatDateTime(fb.created_at)}</span>
                                    </div>
                                    
                                    <div className="flex items-center gap-2">
                                      <CheckCircle2 className="h-4 w-4 text-slate-400 shrink-0" />
                                      <span className="text-slate-500">Trạng thái xử lý:</span>
                                      <span className={`font-semibold ${fb.is_resolved ? "text-emerald-600" : "text-amber-600"}`}>
                                        {fb.is_resolved ? "Đã giải quyết" : "Đang chờ xử lý"}
                                      </span>
                                    </div>

                                    {fb.is_resolved && (
                                      <div className="space-y-2 pt-2 border-t border-slate-100">
                                        <div className="flex items-center gap-2">
                                          <Clock className="h-4 w-4 text-slate-400 shrink-0" />
                                          <span className="text-slate-500">Thời gian xử lý:</span>
                                          <span className="font-medium">{fb.resolved_at ? formatDateTime(fb.resolved_at) : "N/A"}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                          <UserCheck className="h-4 w-4 text-slate-400 shrink-0" />
                                          <span className="text-slate-500">Người xử lý:</span>
                                          <span className="font-semibold text-slate-800">
                                            {fb.resolver ? `${fb.resolver.username} (${fb.resolver.email})` : "Quản trị viên"}
                                          </span>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                </div>

                                <div className="pt-4 flex justify-end">
                                  <button
                                    onClick={(e) => handleToggleResolve(fb, e)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                                      fb.is_resolved 
                                        ? "bg-slate-100 text-slate-600 hover:bg-slate-200 border-slate-200" 
                                        : "bg-orange-600 text-white hover:bg-orange-700 border-transparent shadow-sm"
                                    }`}
                                  >
                                    {fb.is_resolved ? "✓ Đánh dấu Chưa xử lý" : "✓ Đánh dấu Đã xử lý"}
                                  </button>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
