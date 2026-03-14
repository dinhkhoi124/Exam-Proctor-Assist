import { cn } from "@/lib/utils";

interface AudioVisualizerProps {
  isActive: boolean;
  variant?: "recording" | "playing";
  className?: string;
}

export function AudioVisualizer({
  isActive,
  variant = "recording",
  className,
}: AudioVisualizerProps) {
  const bars = variant === "recording" ? 5 : 7;

  return (
    <div
      className={cn(
        "flex items-center justify-center gap-1",
        className
      )}
    >
      {Array.from({ length: bars }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "w-1 rounded-full transition-all duration-200",
            variant === "recording" ? "bg-primary" : "bg-primary/80",
            isActive ? "animate-wave-bar" : "h-2"
          )}
          style={{
            animationDelay: isActive ? `${i * 100}ms` : undefined,
            height: isActive ? undefined : "8px",
          }}
        />
      ))}
    </div>
  );
}
