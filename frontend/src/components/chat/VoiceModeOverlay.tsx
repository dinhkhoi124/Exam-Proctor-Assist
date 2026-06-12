import { useState, useEffect, useCallback, useRef } from "react";
import { X, Mic, MicOff, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AudioVisualizer } from "./AudioVisualizer";
import { cn } from "@/lib/utils";
import { buildApiUrl } from "@/lib/api";

interface VoiceModeOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  onTranscript: (text: string) => void;
}

type VoiceState = "idle" | "listening" | "processing";

export function VoiceModeOverlay({
  isOpen,
  onClose,
  onTranscript,
}: VoiceModeOverlayProps) {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [transcript, setTranscript] = useState("");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const discardRecordingRef = useRef(false);
  const lastSentTextRef = useRef<string>("");

  const startListening = useCallback(async () => {
    try {
      discardRecordingRef.current = false;
      audioChunksRef.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());

        if (discardRecordingRef.current) {
          audioChunksRef.current = [];
          return;
        }

        setVoiceState("processing");

        const mimeType =
          recorder.mimeType || audioChunksRef.current[0]?.type || "audio/webm";
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mimeType,
        });

        console.log("🎧 AUDIO SIZE:", audioBlob.size);

        if (audioBlob.size < 12000) {
          setTranscript("Giọng nói quá ngắn, vui lòng thử lại.");
          setVoiceState("idle");
          return;
        }

        const formData = new FormData();
        const extension = mimeType.includes("ogg")
          ? "ogg"
          : mimeType.includes("mp4")
            ? "m4a"
            : mimeType.includes("wav")
              ? "wav"
              : "webm";
        formData.append("file", audioBlob, `voice.${extension}`);

        try {
          const res = await fetch(buildApiUrl("/api/v1/speech/stt"), {
            method: "POST",
            body: formData,
          });

          if (!res.ok) throw new Error("STT failed");

          const data = await res.json();
          console.log("🎤 STT TEXT:", data.text);

          const cleanText = (data.text || "").trim();

          // 🚫 CHẶN SPAM / TEXT CŨ
          if (
            !cleanText ||
            cleanText.length < 2 ||
            cleanText === lastSentTextRef.current
          ) {
            setTranscript("Không nhận dạng được giọng nói.");
            return;
          }

          lastSentTextRef.current = cleanText;
          setTranscript(cleanText);
          onTranscript(cleanText);
        } catch (err) {
          console.error("STT error:", err);
          setTranscript("Lỗi nhận dạng giọng nói.");
        } finally {
          setVoiceState("idle");
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setTranscript("");
      setVoiceState("listening");
    } catch (err) {
      console.error("Mic error:", err);
      alert("Không thể truy cập microphone");
    }
  }, [onTranscript]);

  const stopListening = useCallback((discard = false) => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      discardRecordingRef.current = discard;
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!isOpen) {
      stopListening(true);
      setVoiceState("idle");
      setTranscript("");
    }
  }, [isOpen, stopListening]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/95 p-4 backdrop-blur-sm">
      <Button variant="ghost" size="icon" className="absolute right-4 top-4" onClick={onClose}>
        <X className="h-6 w-6" />
      </Button>

      <div className="flex flex-col items-center gap-6 px-4">
        <h2 className="text-2xl font-semibold">
          {voiceState === "idle" && "Voice Mode"}
          {voiceState === "listening" && "Listening..."}
          {voiceState === "processing" && "Processing..."}
        </h2>

        <button
          onClick={voiceState === "idle" ? startListening : () => stopListening()}
          disabled={voiceState === "processing"}
          className={cn(
            "flex h-36 w-36 items-center justify-center rounded-full transition",
            voiceState === "idle" && "bg-primary hover:bg-primary/90",
            voiceState === "listening" && "bg-destructive animate-voice-pulse",
            voiceState === "processing" && "bg-secondary"
          )}
        >
          {voiceState === "processing" ? (
            <Volume2 className="h-14 w-14 text-primary-foreground" />
          ) : (
            <Mic className="h-14 w-14 text-primary-foreground" />
          )}
        </button>

        {voiceState === "listening" && (
          <Button variant="outline" onClick={() => stopListening()}>
            <MicOff className="h-4 w-4 mr-2" />
            Dừng thu âm
          </Button>
        )}

        {(voiceState === "listening" || voiceState === "processing") && (
          <AudioVisualizer isActive variant="recording" className="h-12" />
        )}

        {transcript && (
          <div className="max-w-md rounded-xl bg-card border p-4 text-center">
            <p className="text-sm text-muted-foreground mb-1">You said:</p>
            <p className="font-medium">{transcript}</p>
          </div>
        )}
      </div>
    </div>
  );
}
