import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import { format } from "date-fns";
import { Clock, MessageSquare, ChevronRight, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface UserStat {
  id: string;
  username: string;
  email: string;
  question_count: number;
}

interface ChatDetail {
  question: string;
  answer: string;
  topic: string;
  created_at: string;
}

export default function UsersManagement() {
  const [users, setUsers] = useState<UserStat[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Drawer states
  const [selectedUser, setSelectedUser] = useState<UserStat | null>(null);
  const [chats, setChats] = useState<ChatDetail[]>([]);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isChatsLoading, setIsChatsLoading] = useState(false);

  const fetchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const fetchUsers = async () => {
    try {
      const response = await api.get<{users: UserStat[]}>("/api/v1/admin/stats");
      setUsers(response.data.users);
    } catch (err) {
      console.error("Failed to fetch users", err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchUserChats = async (userId: string) => {
    try {
      setIsChatsLoading(true);
      const res = await api.get<ChatDetail[]>(`/api/v1/admin/user/${userId}/chats`);
      setChats(res.data);
    } catch (err) {
      console.error("Failed to fetch chats", err);
    } finally {
      setIsChatsLoading(false);
    }
  };

  const openDrawer = (user: UserStat) => {
    setSelectedUser(user);
    setIsDrawerOpen(true);
    fetchUserChats(user.id);
  };

  const closeDrawer = () => {
    setIsDrawerOpen(false);
    setSelectedUser(null);
    setChats([]);
  };

  // Real-time listener
  useEffect(() => {
    fetchUsers();

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
                fetchUsers();
                if (isDrawerOpen && selectedUser) {
                  fetchUserChats(selectedUser.id);
                }
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
  }, [isDrawerOpen, selectedUser]); // Re-bind if drawer opens to capture selected user context

  return (
    <div className="space-y-6 animate-in fade-in duration-500 pb-10 relative">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">User Management</h1>
        <p className="text-slate-500 mt-1">Track user activities and deep-dive into interaction histories.</p>
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 text-slate-500 border-b">
              <tr>
                <th className="px-6 py-4 font-medium">User Name</th>
                <th className="px-6 py-4 font-medium">Email</th>
                <th className="px-6 py-4 font-medium text-center">Questions Asked</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-slate-400">Loading users...</td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-slate-400">No active users found.</td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 font-medium text-slate-900">{u.username}</td>
                    <td className="px-6 py-4 text-slate-500">{u.email}</td>
                    <td className="px-6 py-4 text-center">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                        {u.question_count}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-orange-600 hover:text-orange-700 hover:bg-orange-50"
                        onClick={() => openDrawer(u)}
                      >
                        View Logs <ChevronRight className="ml-1 h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* OVERLAY */}
      {isDrawerOpen && (
        <div 
          className="fixed inset-0 bg-slate-900/40 z-40 backdrop-blur-sm transition-opacity" 
          onClick={closeDrawer}
        />
      )}

      {/* SIDE DRAWER */}
      <div 
        className={`fixed top-0 right-0 h-full w-full sm:w-[450px] bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col ${
          isDrawerOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b bg-slate-50">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{selectedUser?.username}</h2>
            <p className="text-sm text-slate-500">{selectedUser?.email}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={closeDrawer} className="text-slate-500 hover:text-slate-900">
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-6 custom-scrollbar bg-white">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-6">Interaction Timeline</h3>
          
          {isChatsLoading ? (
            <div className="text-center text-slate-400 text-sm mt-10 animate-pulse">Loading history...</div>
          ) : chats.length === 0 ? (
            <div className="text-center text-slate-400 text-sm mt-10">No interactions recorded.</div>
          ) : (
            <div className="space-y-8 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-300 before:to-transparent">
              {chats.map((chat, idx) => (
                <div key={idx} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                  
                  {/* Icon */}
                  <div className="flex items-center justify-center w-10 h-10 rounded-full border border-white bg-slate-100 text-slate-500 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
                    <MessageSquare className="h-4 w-4" />
                  </div>
                  
                  {/* Content Card */}
                  <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] pb-4">
                    <div className="p-4 rounded-xl border bg-white shadow-[0_1px_3px_0_rgb(0,0,0,0.05)] hover:shadow-md transition-shadow flex flex-col gap-1.5">
                      <div className="self-start mb-0.5">
                        <span className="text-xs font-bold px-2.5 py-1 bg-orange-100 text-orange-700 rounded-md inline-block">
                          {chat.topic}
                        </span>
                      </div>
                      <time className="text-xs text-slate-400 flex items-center gap-1 font-medium">
                        <Clock className="w-3 h-3" />
                        {format(new Date(chat.created_at), "HH:mm - dd/MM/yyyy")}
                      </time>
                      <div className="text-sm font-medium text-slate-900 leading-snug mt-1">
                        {chat.question}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
