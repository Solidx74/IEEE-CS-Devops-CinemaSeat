import { cn } from "@/lib/utils";
import type { BookingStep } from "@/types/booking";
import { Check } from "lucide-react";

const STEPS: { key: BookingStep; label: string }[] = [
  { key: "browse", label: "Browse" },
  { key: "seats", label: "Seat Map" },
  { key: "hold", label: "Hold" },
  { key: "pay", label: "Pay" },
  { key: "ticket", label: "Ticket" },
];

export function StepIndicator({ current }: { current: BookingStep }) {
  const activeIndex = STEPS.findIndex((s) => s.key === current);

  return (
    <nav aria-label="Booking progress" className="w-full">
      <ol className="flex items-center gap-1 sm:gap-2">
        {STEPS.map((step, i) => {
          const done = i < activeIndex;
          const active = i === activeIndex;
          return (
            <li key={step.key} className="flex min-w-0 flex-1 items-center gap-1 sm:gap-2">
              <div className="flex min-w-0 items-center gap-2">
                <span
                  className={cn(
                    "grid h-7 w-7 shrink-0 place-items-center rounded-full text-[11px] font-semibold transition-all duration-300",
                    done && "bg-gold/20 text-gold",
                    active && "bg-gold text-gold-foreground shadow-glow-gold",
                    !done && !active && "bg-secondary text-muted-foreground",
                  )}
                >
                  {done ? <Check className="h-3.5 w-3.5" /> : i + 1}
                </span>
                <span
                  className={cn(
                    "hidden truncate font-display text-xs uppercase tracking-[0.14em] transition-colors sm:inline",
                    active ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <span className="h-px flex-1 bg-border">
                  <span
                    className={cn(
                      "block h-px origin-left bg-gold transition-transform duration-500",
                      done ? "scale-x-100" : "scale-x-0",
                    )}
                  />
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
