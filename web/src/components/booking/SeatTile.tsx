import { cn } from "@/lib/utils";
import type { Seat } from "@/types/booking";

interface SeatTileProps {
  seat: Seat;
  selected: boolean;
  onSelect: (seat: Seat) => void;
}

export function SeatTile({ seat, selected, onSelect }: SeatTileProps) {
  const premium = seat.seat_type === "PREMIUM";
  const disabled = seat.status !== "AVAILABLE";

  return (
    <button
      type="button"
      disabled={disabled}
      aria-pressed={selected}
      aria-label={`Seat ${seat.row_label}${seat.seat_number}, ${seat.seat_type.toLowerCase()}, ${seat.status.toLowerCase()}`}
      onClick={() => onSelect(seat)}
      className={cn(
        "relative h-8 w-8 shrink-0 rounded-[7px] text-[10px] font-medium shadow-seat transition-all duration-200 sm:h-9 sm:w-9 sm:text-[11px]",
        "focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring",
        !disabled &&
          !selected &&
          "hover:-translate-y-0.5 hover:scale-110 hover:shadow-glow-gold",
        seat.status === "AVAILABLE" &&
          !selected &&
          !premium &&
          "border border-success/40 bg-surface-2 text-foreground/80 hover:border-success",
        seat.status === "AVAILABLE" &&
          !selected &&
          premium &&
          "border border-gold/60 bg-gold/12 text-gold hover:border-gold",
        selected &&
          "animate-seat-pop border border-gold bg-gold font-semibold text-gold-foreground shadow-glow-gold",
        seat.status === "HELD" &&
          "cursor-not-allowed border border-urgent/45 bg-urgent/15 text-urgent/80",
        seat.status === "BOOKED" &&
          "cursor-not-allowed border border-border bg-secondary text-muted-foreground/50 line-through",
      )}
    >
      {seat.seat_number}
      {premium && seat.status === "AVAILABLE" && !selected && (
        <span
          aria-hidden
          className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-gold"
        />
      )}
    </button>
  );
}
