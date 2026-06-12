import { useState, useRef, useEffect, useCallback } from "react";
import { GraduationCap, Search, MessageSquare, Edit3, Trash2, Check, X } from "lucide-react";
import { ChatMessage, Message } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";
import { QuickActions } from "./QuickActions";
import { VoiceModeOverlay } from "./VoiceModeOverlay";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface ChatSessionItem {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isVoiceModeOpen, setIsVoiceModeOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Chat Sessions States
  const [sessions, setSessions] = useState<ChatSessionItem[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  
  // Editing session title states
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // Load user sessions list on mount
  const fetchSessions = async () => {
    try {
      const res = await api.get<ChatSessionItem[]>("/api/v1/chat/sessions");
      setSessions(res.data);
    } catch (err) {
      console.error("Failed to load chat sessions", err);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  // Fetch session history messages
  const loadSessionHistory = async (sessionId: string) => {
    try {
      setIsLoading(true);
      const res = await api.get<any[]>(`/api/v1/chat/sessions/${sessionId}/history`);
      const mappedMessages: Message[] = res.data.map((m: any) => ({
        id: m.id,
        chatLogId: m.id.includes('_') ? m.id.split('_')[0] : m.id,
        role: m.role,
        content: m.content,
        timestamp: new Date(m.timestamp),
        type: "text"
      }));
      setMessages(mappedMessages);
    } catch (err) {
      console.error("Failed to load chat history", err);
      toast.error("Không thể tải lịch sử cuộc trò chuyện");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectSession = (sessionId: string) => {
    if (editingSessionId) return; // Prevent switching while renaming
    setCurrentSessionId(sessionId);
    loadSessionHistory(sessionId);
  };

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
  };

  const handleRenameSessionSubmit = async (sessionId: string) => {
    if (!editingTitle.trim()) {
      toast.error("Tiêu đề không được để trống");
      return;
    }
    try {
      await api.put(`/api/v1/chat/sessions/${sessionId}`, { title: editingTitle });
      toast.success("Đổi tên cuộc trò chuyện thành công");
      setEditingSessionId(null);
      setEditingTitle("");
      fetchSessions();
    } catch (err) {
      console.error("Failed to rename session", err);
      toast.error("Không thể đổi tên cuộc trò chuyện");
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Avoid selecting session on click
    if (!confirm("Bạn có chắc chắn muốn xóa cuộc trò chuyện này?")) return;
    
    try {
      await api.delete(`/api/v1/chat/sessions/${sessionId}`);
      toast.success("Đã xóa cuộc trò chuyện");
      fetchSessions();
      if (currentSessionId === sessionId) {
        handleNewChat();
      }
    } catch (err) {
      console.error("Failed to delete session", err);
      toast.error("Xóa cuộc trò chuyện thất bại");
    }
  };

  const handleSendMessage = useCallback(
    async (content: string, type: "text" | "image" | "voice" = "text", imageUrl?: string) => {
      const userMessage: Message = {
        id: Date.now().toString(),
        role: "user",
        content,
        timestamp: new Date(),
        type,
        imageUrl, 
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      try {
        const response = await api.post("/api/v1/chat", {
          message: content,
          image: imageUrl || null,
          session_id: currentSessionId
        });

        const data = response.data;

        // If a new session was created dynamically on the first message
        if (!currentSessionId && data.session_id) {
          setCurrentSessionId(data.session_id);
          fetchSessions();
        }

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          chatLogId: data.chat_log_id,
          role: "assistant",
          content: data.answer || "No response",
          timestamp: new Date(),
          type: "text",
          pageImages: data.page_images || [], 
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 2).toString(),
            role: "assistant",
            content: "⚠️ Không kết nối được hệ thống. Vui lòng kiểm tra lại kết nối server.",
            timestamp: new Date(),
            type: "text",
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [currentSessionId]
  );

  const handleVoiceTranscript = useCallback(
    (text: string) => {
      handleSendMessage(text, "voice");
      setIsVoiceModeOpen(false);
    },
    [handleSendMessage]
  );

  // Filter sessions list based on local search query
  const filteredSessions = sessions.filter(s =>
    s.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden">
      {/* CHAT SESSION SIDEBAR */}
      <aside className="w-64 bg-slate-50 border-r flex flex-col shrink-0 hidden md:flex">
        {/* New Chat Button Area */}
        <div className="p-4 border-b space-y-3">
          <Button 
            onClick={handleNewChat}
            className="w-full bg-orange-600 hover:bg-orange-700 text-white text-xs font-semibold py-2 rounded-lg flex items-center justify-center gap-2"
          >
            + Cuộc trò chuyện mới
          </Button>
        </div>

        {/* Search Input Area */}
        <div className="p-3 border-b">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Tìm kiếm cuộc trò chuyện..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-lg border text-xs bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-orange-500 focus:border-orange-500"
            />
          </div>
        </div>

        {/* Session List Area */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
          {sessions.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-400 p-4 space-y-2">
              <MessageSquare className="h-8 w-8 text-slate-350" />
              <div className="space-y-0.5">
                <span className="text-xs font-semibold text-slate-500 block">Lịch sử trống</span>
                <p className="text-[10px] text-slate-400 max-w-[180px]">
                  Bắt đầu cuộc trò chuyện mới để lưu lịch sử hội thoại của bạn.
                </p>
              </div>
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="text-center text-xs text-slate-400 p-4">Không tìm thấy cuộc trò chuyện.</div>
          ) : (
            filteredSessions.map((session) => {
              const isSelected = currentSessionId === session.id;
              const isEditing = editingSessionId === session.id;

              return (
                <div
                  key={session.id}
                  onClick={() => handleSelectSession(session.id)}
                  className={`w-full group px-3 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer flex items-center justify-between gap-2 border ${
                    isSelected 
                      ? "bg-orange-100/70 border-orange-200 text-orange-800" 
                      : "border-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <MessageSquare className={`h-4 w-4 shrink-0 ${isSelected ? "text-orange-600" : "text-slate-400"}`} />
                    {isEditing ? (
                      <input
                        type="text"
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleRenameSessionSubmit(session.id);
                          if (e.key === "Escape") setEditingSessionId(null);
                        }}
                        onClick={(e) => e.stopPropagation()} // Stop switching conversation when typing
                        className="w-full px-1 py-0.5 border rounded focus:outline-none focus:ring-1 focus:ring-orange-500 text-slate-900 text-xxs font-normal bg-white"
                        autoFocus
                      />
                    ) : (
                      <span className="truncate text-left font-semibold">{session.title}</span>
                    )}
                  </div>

                  {/* Actions buttons */}
                  {!isEditing && isSelected && (
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingSessionId(session.id);
                          setEditingTitle(session.title);
                        }}
                        className="p-1 hover:bg-orange-200 text-orange-700 rounded transition-colors"
                      >
                        <Edit3 className="h-3 w-3" />
                      </button>
                      <button
                        onClick={(e) => handleDeleteSession(session.id, e)}
                        className="p-1 hover:bg-red-200 text-red-700 rounded transition-colors"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  )}

                  {isEditing && (
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRenameSessionSubmit(session.id);
                        }}
                        className="p-0.5 hover:bg-orange-200 text-orange-700 rounded"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingSessionId(null);
                        }}
                        className="p-0.5 hover:bg-slate-200 text-slate-700 rounded"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* MAIN CHAT WINDOW */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <div className="flex-1 overflow-y-auto chat-scrollbar bg-chat-bg">
          <div className="mx-auto max-w-3xl px-4 py-6">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-primary/10 animate-float">
                  <GraduationCap className="h-10 w-10 text-primary" />
                </div>
                <h2 className="mb-2 text-2xl font-bold text-foreground">
                  Exam Proctor Support
                </h2>
                <p className="mb-8 max-w-md text-center text-muted-foreground">
                  Hệ thống AI hỗ trợ Cán bộ coi thi và Giám thị xử lý sự cố kỹ thuật trong phòng thi EOS/PEA.
                </p>
                <QuickActions onSelect={(query) => handleSendMessage(query)} />
              </div>
            ) : (
              <div className="space-y-6">
                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
                {isLoading && <TypingIndicator />}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>

        <ChatInput
          onSendMessage={handleSendMessage}
          onOpenVoiceMode={() => setIsVoiceModeOpen(true)}
          isLoading={isLoading}
        />

        <VoiceModeOverlay
          isOpen={isVoiceModeOpen}
          onClose={() => setIsVoiceModeOpen(false)}
          onTranscript={handleVoiceTranscript}
        />
      </div>
    </div>
  );
}