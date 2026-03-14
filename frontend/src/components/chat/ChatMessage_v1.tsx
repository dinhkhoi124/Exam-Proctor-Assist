import { cn } from "@/lib/utils";
import { Bot, User, Image as ImageIcon, Mic, FileSearch } from "lucide-react";

// Cấu trúc cho từng trang ảnh hướng dẫn
interface PageImage {
  page: number;
  base64: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  type?: "text" | "image" | "voice";
  imageUrl?: string; // Ảnh do người dùng gửi
  pageImages?: PageImage[]; // ✅ MỚI: Danh sách nhiều trang ảnh hướng dẫn
}

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  const getRenderableImageUrl = (url: string) => {
    if (url && !url.startsWith("data:") && !url.startsWith("http")) {
      return `data:image/jpeg;base64,${url}`;
    }
    return url;
  };

  return (
    <div
      className={cn(
        "flex gap-3 animate-fade-in-up",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-secondary text-secondary-foreground border border-border",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Message Content */}
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-3 shadow-chat",
          isUser
            ? "bg-primary text-primary-foreground rounded-tr-md"
            : "bg-card text-card-foreground border border-border rounded-tl-md",
        )}
      >
        {/* Type indicator (Image/Voice) */}
        {message.type && message.type !== "text" && (
          <div
            className={cn(
              "mb-2 flex items-center gap-1.5 text-xs",
              isUser ? "text-primary-foreground/70" : "text-muted-foreground",
            )}
          >
            {message.type === "image" && (
              <>
                <ImageIcon className="h-3 w-3" />
                <span>Image attached</span>
              </>
            )}
            {message.type === "voice" && (
              <>
                <Mic className="h-3 w-3" />
                <span>Voice message</span>
              </>
            )}
          </div>
        )}

        {/* User's uploaded image */}
        {message.imageUrl && (
          <div className="mb-2 overflow-hidden rounded-lg border border-border/50">
            <img
              src={getRenderableImageUrl(message.imageUrl)}
              alt="User Attached"
              className="max-h-60 w-auto object-contain bg-muted"
            />
          </div>
        )}

        {/* Text content */}
        <div
          className={cn(
            "prose prose-sm max-w-none",
            isUser ? "prose-invert" : "prose-gray",
          )}
        >
          {message.content.split("\n").map((line, i) => {
            if (line.startsWith("**") && line.endsWith("**")) {
              return (
                <p key={i} className="font-semibold mb-2">
                  {line.replace(/\*\*/g, "")}
                </p>
              );
            }
            if (line.match(/^\d+\.\s/)) {
              return (
                <p key={i} className="ml-2 mb-1">
                  {line.replace(/\*\*(.*?)\*\*/g, (_, text) => text)}
                </p>
              );
            }
            if (line.trim()) {
              return (
                <p key={i} className="mb-1">
                  {line.replace(/\*\*(.*?)\*\*/g, (_, text) => text)}
                </p>
              );
            }
            return <br key={i} />;
          })}
        </div>

        {/* ✅ PHẦN MỚI: Danh sách ảnh trích xuất từ PDF (Giống mẫu) */}
        {!isUser && message.pageImages && message.pageImages.length > 0 && (
          <div className="mt-4 pt-3 border-t border-orange-100 space-y-4">
            {message.pageImages.map((imgObj, idx) => (
              <div key={idx} className="space-y-2 group">
                {/* Header "Trang n" */}
                <div className="flex items-center gap-2 text-xs font-bold text-orange-600">
                  <FileSearch className="h-3.5 w-3.5" />
                  <span>Trang {imgObj.page}</span>
                </div>

                {/* Image Container */}
                <div
                  className="overflow-hidden rounded-xl border border-orange-200 bg-white shadow-sm cursor-zoom-in relative"
                  onClick={() =>
                    window.open(
                      `data:image/png;base64,${imgObj.base64}`,
                      "_blank",
                    )
                  }
                >
                  <img
                    src={`data:image/png;base64,${imgObj.base64}`}
                    alt={`Hướng dẫn trang ${imgObj.page}`}
                    className="w-full h-auto object-contain transition-transform duration-300 group-hover:scale-[1.01]"
                  />
                  <div className="absolute inset-0 bg-orange-900/0 group-hover:bg-orange-900/5 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                    <span className="bg-white/90 text-[10px] px-2 py-1 rounded-md shadow-sm text-orange-700 font-bold border border-orange-100">
                      Click to enlarge
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <div
          className={cn(
            "mt-2 text-[10px]",
            isUser ? "text-primary-foreground/60" : "text-muted-foreground",
          )}
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </div>
  );
}
