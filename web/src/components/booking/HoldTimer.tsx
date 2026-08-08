import { cn } from "@/lib/utils";
import { formatClock } from "@/lib/format";

interface HoldTimerProps {
  remaining: number;
  total: number;
  size?: number;
}

export function HoldTimer({ remaining, total, size = 168 }: HoldTimerProps) {
  const safeTotal = total > 0 ? total : 1;
  const progress = Math.min(1, Math.max(0, remaining / safeTotal));
  const urgent = remaining <= Math.min(30, safeTotal * 0.25);
  const radius = (size - 14) / 2;
  const circumference = 2 * Math.PI * radius;

  return (
    <div
      className="relative grid place-items-center"
      style={{ width: size, height: size }}
      role="timer"
      aria-live="off"
    >
      <div
        aria-hidden
        className={cn(
          "absolute inset-4 rounded-full blur-2xl transition-colors duration-500",
          urgent ? "bg-urgent/25" : "bg-gold/20",
        )}
      />
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-90"
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={7}
          className="stroke-border"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={7}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - progress)}
          className={cn(
            "transition-[stroke-dashoffset,stroke] duration-1000 ease-linear",
            urgent ? "stroke-urgent" : "stroke-gold",
          )}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span
          className={cn(
            "font-mono text-3xl font-semibold tabular-nums transition-colors duration-500",
            urgent ? "text-urgent" : "text-gold",
          )}
        >
          {formatClock(remaining)}
        </span>
        <span className="mt-1 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          {remaining > 0 ? "Seat held" : "Expired"}
        </span>
      </div>
    </div>
  );
}
