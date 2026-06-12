import { useState } from "react";
import { cn } from "@/lib/utils";
import { Bot, User, Image as ImageIcon, Mic, FileSearch, ThumbsUp, ThumbsDown } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";

// Cấu trúc cho từng trang ảnh hướng dẫn
interface PageImage {
  page: number;
  base64: string;
}

export interface Message {
  id: string;
  chatLogId?: string; // ID lưu trữ trong DB để đánh giá phản hồi
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  type?: "text" | "image" | "voice";
  imageUrl?: string; // Ảnh do người dùng gửi
  pageImages?: PageImage[]; // Danh sách nhiều trang ảnh hướng dẫn
}

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const [showImages, setShowImages] = useState(false);

  // States cho Feedback
  const [feedbackRating, setFeedbackRating] = useState<"like" | "dislike" | null>(null);
  const [showCommentForm, setShowCommentForm] = useState(false);
  const [commentText, setCommentText] = useState("");
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const getRenderableImageUrl = (url: string) => {
    if (url && !url.startsWith("data:") && !url.startsWith("http")) {
      return `data:image/jpeg;base64,${url}`;
    }
    return url;
  };

  const handleLike = async () => {
    if (!message.chatLogId) return;
    setIsSubmitting(true);
    try {
      await api.post("/api/v1/feedback", {
        chat_id: message.chatLogId,
        rating: "like",
        comment: null
      });
      setFeedbackRating("like");
      setIsSubmitted(true);
      toast.success("Cảm ơn bạn đã phản hồi!");
    } catch (error) {
      console.error("Failed to submit feedback", error);
      toast.error("Không thể gửi phản hồi. Vui lòng thử lại.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDislike = () => {
    setFeedbackRating("dislike");
    setShowCommentForm(true);
  };

  const handleSubmitComment = async () => {
    if (!message.chatLogId || !commentText.trim()) return;
    setIsSubmitting(true);
    try {
      await api.post("/api/v1/feedback", {
        chat_id: message.chatLogId,
        rating: "dislike",
        comment: commentText.trim()
      });
      setIsSubmitted(true);
      setShowCommentForm(false);
      toast.success("Cảm ơn ý kiến đóng góp của bạn!");
    } catch (error) {
      console.error("Failed to submit feedback comment", error);
      toast.error("Không thể gửi góp ý. Vui lòng thử lại.");
    } finally {
      setIsSubmitting(false);
    }
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
                  {line.replace(/\*\/g/g, "").replace(/\*\*/g, "")}
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

        {/* Danh sách ảnh trích xuất từ PDF */}
        {!isUser &&
          showImages &&
          message.pageImages &&
          message.pageImages.length > 0 && (
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

        {/* Actions row: Source slide, Timestamp, and Feedback */}
        <div className="mt-2.5 pt-1.5 border-t border-slate-100/60 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {/* Timestamp */}
            <span
              className={cn(
                "text-[10px]",
                isUser ? "text-primary-foreground/60" : "text-muted-foreground",
              )}
            >
              {message.timestamp.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>

            {/* Button toggle hiển thị slide */}
            {!isUser && message.pageImages && message.pageImages.length > 0 && (
              <button
                onClick={() => setShowImages(!showImages)}
                className="text-[10px] font-semibold text-orange-600 hover:text-orange-700 flex items-center gap-1"
              >
                <FileSearch className="h-3 w-3" />
                {showImages ? "Ẩn slide" : "Xem slide"}
              </button>
            )}
          </div>

          {/* Thumbs Up / Down feedback for Assistant replies */}
          {!isUser && message.chatLogId && (
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                disabled={isSubmitted || isSubmitting}
                onClick={handleLike}
                className={cn(
                  "p-1 rounded hover:bg-slate-100 transition-colors",
                  feedbackRating === "like" ? "text-green-600 bg-green-50 hover:bg-green-50" : "text-slate-400 hover:text-slate-600"
                )}
                title="Hài lòng với câu trả lời"
              >
                <ThumbsUp className="h-3.5 w-3.5" />
              </button>
              <button
                disabled={isSubmitted || isSubmitting}
                onClick={handleDislike}
                className={cn(
                  "p-1 rounded hover:bg-slate-100 transition-colors",
                  feedbackRating === "dislike" ? "text-red-600 bg-red-50 hover:bg-red-50" : "text-slate-400 hover:text-slate-600"
                )}
                title="Chưa hài lòng với câu trả lời"
              >
                <ThumbsDown className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Comment input form for dislike */}
        {showCommentForm && (
          <div className="mt-3 p-2 border border-slate-100 rounded-lg bg-slate-50/50 space-y-2">
            <div className="text-[10px] font-semibold text-slate-500">
              Hãy giúp chúng tôi cải thiện câu trả lời:
            </div>
            <textarea
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="Nhập ý kiến đóng góp của bạn tại đây..."
              rows={2}
              className="w-full p-1.5 text-xs border rounded-lg focus:outline-none focus:ring-1 focus:ring-orange-500 text-slate-800 bg-white"
            />
            <div className="flex justify-end gap-1.5">
              <button
                onClick={() => {
                  setShowCommentForm(false);
                  setFeedbackRating(null);
                }}
                className="px-2 py-1 text-[10px] font-semibold text-slate-500 hover:bg-slate-100 rounded"
              >
                Hủy
              </button>
              <button
                disabled={isSubmitting || !commentText.trim()}
                onClick={handleSubmitComment}
                className="px-2.5 py-1 text-[10px] font-semibold bg-orange-600 text-white hover:bg-orange-700 disabled:opacity-50 rounded"
              >
                {isSubmitting ? "Đang gửi..." : "Gửi góp ý"}
              </button>
            </div>
          </div>
        )}

        {isSubmitted && feedbackRating === "dislike" && (
          <div className="mt-2 text-[10px] text-green-700 font-medium bg-green-50/80 px-2 py-1 rounded border border-green-100">
            ✓ Đã gửi góp ý cải thiện. Cảm ơn bạn!
          </div>
        )}
      </div>
    </div>
  );
}

