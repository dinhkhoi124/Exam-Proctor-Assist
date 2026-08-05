import { useState, useRef, KeyboardEvent } from "react";
import { Send, Image as ImageIcon, Mic, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { AudioVisualizer } from "./AudioVisualizer";
import { cn } from "@/lib/utils";
import { buildApiUrl } from "@/lib/api";
import { toast } from "sonner";

interface ChatInputProps {
  onSendMessage: (
    message: string,
    type?: "text" | "image" | "voice",
    imageUrl?: string,
  ) => void;
  onOpenVoiceMode: () => void;
  isLoading: boolean;
}

export function ChatInput({
  onSendMessage,
  onOpenVoiceMode,
  isLoading,
}: ChatInputProps) {
  const [message, setMessage] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [attachedImage, setAttachedImage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const getAudioFileName = (mimeType: string) => {
    if (mimeType.includes("ogg")) return "recording.ogg";
    if (mimeType.includes("mp4")) return "recording.m4a";
    if (mimeType.includes("wav")) return "recording.wav";
    return "recording.webm";
  };

  const handleSend = () => {
    if (message.trim() || attachedImage) {
      // ✅ BẢN CHỈNH SỬA: Lấy phần data thuần từ Base64 để gửi lên API Backend
      const base64Content = attachedImage
        ? attachedImage.split(",")[1]
        : undefined;

      onSendMessage(
        message.trim() || "Hãy phân tích hình ảnh lỗi này.",
        attachedImage ? "image" : "text",
        base64Content, // Truyền phần content đã loại bỏ header metadata
      );

      setMessage("");
      setAttachedImage(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleVoiceRecord = async () => {
    if (isRecording) {
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
        setIsRecording(false);
      }
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) audioChunksRef.current.push(event.data);
        };

        mediaRecorder.onstop = async () => {
          stream.getTracks().forEach((track) => track.stop());
          mediaRecorderRef.current = null;

          const mimeType =
            mediaRecorder.mimeType ||
            audioChunksRef.current[0]?.type ||
            "audio/webm";
          const audioBlob = new Blob(audioChunksRef.current, {
            type: mimeType,
          });
          const formData = new FormData();
          formData.append("file", audioBlob, getAudioFileName(mimeType));
          setIsTranscribing(true);

          try {
            const response = await fetch(buildApiUrl("/api/v1/speech/stt"), {
              method: "POST",
              body: formData,
            });

            if (response.ok) {
              const data = await response.json();
              if (data.text && data.text.trim() !== "") {
                onSendMessage(data.text, "voice");
              } else {
                toast.error("Không nhận dạng được giọng nói. Vui lòng thử lại.");
              }
            } else {
              const errorBody = await response.json().catch(() => null);
              console.error("Lỗi Backend:", response.status, errorBody);
              toast.error(
                errorBody?.detail || "Không thể nhận dạng giọng nói.",
              );
            }
          } catch (error) {
            console.error("Lỗi kết nối:", error);
            toast.error("Không thể kết nối dịch vụ nhận dạng giọng nói.");
          } finally {
            setIsTranscribing(false);
          }
        };

        mediaRecorder.start();
        setIsRecording(true);
      } catch (err) {
        console.error("Lỗi Micro:", err);
        toast.error("Không thể truy cập microphone. Vui lòng kiểm tra quyền trình duyệt.");
      }
    }
  };

  return (
    <div className="border-t border-border bg-card p-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] sm:p-4">
      <div className="mx-auto max-w-3xl">
        {attachedImage && (
          <div className="mb-3 flex items-start gap-2 rounded-lg bg-secondary/50 p-2">
            <div className="relative">
              <img
                src={attachedImage}
                alt="Attached"
                className="h-20 w-20 rounded-lg object-cover"
              />
              <button
                onClick={() => {
                  setAttachedImage(null);
                  if (fileInputRef.current) fileInputRef.current.value = "";
                }}
                className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          </div>
        )}

        {isRecording && (
          <div className="mb-3 flex items-center gap-3 rounded-lg bg-primary/10 p-3">
            <div className="h-3 w-3 rounded-full bg-destructive animate-pulse" />
            <span className="text-sm font-medium text-foreground">
              Recording...
            </span>
            <AudioVisualizer
              isActive={true}
              variant="recording"
              className="flex-1"
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                if (mediaRecorderRef.current) mediaRecorderRef.current.stop();
                setIsRecording(false);
              }}
              className="text-destructive"
            >
              Stop &amp; send
            </Button>
          </div>
        )}

        {isTranscribing && (
          <div className="mb-3 flex items-center gap-3 rounded-lg bg-primary/10 p-3">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span className="text-sm font-medium text-foreground">
              Converting voice to text...
            </span>
          </div>
        )}

        <div className="flex items-end gap-1.5 sm:gap-2">
          <div className="flex shrink-0 gap-0 sm:gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-11 w-10 text-muted-foreground"
              onClick={() => fileInputRef.current?.click()}
              aria-label="Đính kèm hình ảnh"
              disabled={isLoading || isTranscribing}
            >
              <ImageIcon className="h-5 w-5" />
            </Button>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-11 w-10",
                    isRecording ? "text-destructive" : "text-muted-foreground",
                  )}
                  onClick={handleVoiceRecord}
                  aria-label={isRecording ? "Dừng ghi âm" : "Ghi âm"}
                  disabled={isLoading || isTranscribing}
                >
                  <Mic className="h-5 w-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {isRecording ? "Stop recording" : "Voice message"}
              </TooltipContent>
            </Tooltip>
          </div>

          <div className="relative min-w-0 flex-1">
            <Textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe the issue..."
              className="min-h-[44px] max-h-32 resize-none rounded-xl border-border bg-background text-sm [font-size:16px] sm:[font-size:14px]"
              disabled={isLoading || isRecording || isTranscribing}
              rows={1}
            />
          </div>

          <Button
            size="icon"
            className="h-11 w-11 shrink-0 rounded-xl"
            onClick={handleSend}
            aria-label="Gửi tin nhắn"
            disabled={
              isLoading ||
              isRecording ||
              isTranscribing ||
              (!message.trim() && !attachedImage)
            }
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </Button>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              const reader = new FileReader();
              reader.onload = () => setAttachedImage(reader.result as string);
              reader.readAsDataURL(file);
            }
          }}
        />
      </div>
    </div>
  );
}
