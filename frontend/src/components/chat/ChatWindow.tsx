import { useState, useRef, useEffect, useCallback } from "react";
import { GraduationCap } from "lucide-react";
import { ChatMessage, Message } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";
import { QuickActions } from "./QuickActions";
import { VoiceModeOverlay } from "./VoiceModeOverlay";
import { api } from "@/lib/api";

export function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isVoiceModeOpen, setIsVoiceModeOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  const handleSendMessage = useCallback(
    async (content: string, type: "text" | "image" | "voice" = "text", imageUrl?: string) => {
      // 1. Tạo object tin nhắn của người dùng
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
        });

        const data = response.data;

        // 3. Xử lý phản hồi từ Assistant
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: data.answer || "No response",
          timestamp: new Date(),
          type: "text",
          // ✅ CẬP NHẬT: Nhận danh sách page_images từ Backend response
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
    []
  );

  const handleVoiceTranscript = useCallback(
    (text: string) => {
      handleSendMessage(text, "voice");
      setIsVoiceModeOpen(false);
    },
    [handleSendMessage]
  );

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
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
                Hệ thống hỗ trợ xử lý lỗi kỹ thuật thi EOS. Trích xuất hướng dẫn trực tiếp từ tài liệu PDF.
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
  );
}