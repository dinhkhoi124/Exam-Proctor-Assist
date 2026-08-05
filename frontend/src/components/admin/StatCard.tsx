import { ReactNode, useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  icon?: ReactNode;
  className?: string;
}

export function StatCard({ title, value, icon, className }: StatCardProps) {
  const [displayValue, setDisplayValue] = useState<string | number>(value);
  const [isHighlight, setIsHighlight] = useState(false);
  
  const prevValueRef = useRef<string | number>(value);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    const prevVal = prevValueRef.current;
    prevValueRef.current = value;

    // Trigger highlight when value changes (and it's not the initial mount)
    if (prevVal !== value) {
      setIsHighlight(true);
      const timer = setTimeout(() => setIsHighlight(false), 1200);

      // Handle count-up animation if values are numbers
      const startNum = typeof prevVal === "number" ? prevVal : parseInt(String(prevVal), 10);
      const endNum = typeof value === "number" ? value : parseInt(String(value), 10);

      if (!isNaN(startNum) && !isNaN(endNum)) {
        const duration = 800; // 800ms
        const startTime = performance.now();

        const animate = (now: number) => {
          const elapsed = now - startTime;
          const progress = Math.min(elapsed / duration, 1);
          
          // Easing: easeOutQuad
          const easeProgress = progress * (2 - progress);
          const currentVal = Math.round(startNum + (endNum - startNum) * easeProgress);
          
          setDisplayValue(currentVal);

          if (progress < 1) {
            animationRef.current = requestAnimationFrame(animate);
          } else {
            setDisplayValue(endNum);
          }
        };

        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
        animationRef.current = requestAnimationFrame(animate);
      } else {
        setDisplayValue(value);
      }

      return () => {
        clearTimeout(timer);
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
      };
    } else {
      setDisplayValue(value);
    }
  }, [value]);

  return (
    <div
      className={cn(
        "rounded-xl border bg-card text-card-foreground shadow transition-all duration-500 hover:-translate-y-1 hover:shadow-lg relative overflow-hidden",
        isHighlight 
          ? "border-orange-500 bg-orange-50/50 scale-[1.02] shadow-orange-100/50" 
          : "border-border",
        className
      )}
    >
      {/* Light glow background when highlighted */}
      <div 
        className={cn(
          "absolute inset-0 bg-gradient-to-tr from-orange-500/0 via-orange-500/0 to-orange-500/5 transition-opacity duration-500 pointer-events-none",
          isHighlight ? "opacity-100" : "opacity-0"
        )} 
      />

      <div className="p-6 flex flex-row items-center justify-between space-y-0 pb-2">
        <h3 className="tracking-tight text-sm font-medium text-slate-500">{title}</h3>
        {icon && <div className="h-4 w-4 text-muted-foreground">{icon}</div>}
      </div>
      <div className="p-6 pt-0">
        <div 
          className={cn(
            "text-2xl font-bold transition-all duration-300", 
            isHighlight ? "text-orange-600 scale-105" : "text-slate-900"
          )}
        >
          {displayValue}
        </div>
      </div>
    </div>
  );
}
