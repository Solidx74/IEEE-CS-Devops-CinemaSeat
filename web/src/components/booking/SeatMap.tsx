import { useMemo } from "react";
import type { Seat } from "@/types/booking";
import { ScreenBar } from "./ScreenBar";
import { SeatLegend } from "./SeatLegend";
import { SeatTile } from "./SeatTile";

interface SeatMapProps {
  seats: Seat[];
  selectedSeatId: string | null;
  onSelect: (seat: Seat) => void;
}

export function SeatMap({ seats, selectedSeatId, onSelect }: SeatMapProps) {
  const rows = useMemo(() => {
    const map = new Map<string, Seat[]>();
    for (const seat of seats) {
      const list = map.get(seat.row_label) ?? [];
      list.push(seat);
      map.set(seat.row_label, list);
    }
    return [...map.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([row, list]) => ({
        row,
        seats: [...list].sort((a, b) => a.seat_number - b.seat_number),
      }));
  }, [seats]);

  return (
    <section className="surface-card vignette relative overflow-hidden px-3 py-8 sm:px-6 sm:py-10">
      <ScreenBar />

      <div className="-mx-3 overflow-x-auto px-3 pb-2 sm:mx-0 sm:px-0">
        <div className="mx-auto flex w-max min-w-full flex-col items-center gap-2">
          {rows.map(({ row, seats: rowSeats }) => (
            <div key={row} className="flex items-center gap-3">
              <span className="w-5 shrink-0 text-right font-mono text-[11px] text-muted-foreground">
                {row}
              </span>
              <div className="flex gap-1.5 sm:gap-2">
                {rowSeats.map((seat) => (
                  <SeatTile
                    key={seat.id}
                    seat={seat}
                    selected={seat.id === selectedSeatId}
                    onSelect={onSelect}
                  />
                ))}
              </div>
              <span className="w-5 shrink-0 font-mono text-[11px] text-muted-foreground">
                {row}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-8">
        <SeatLegend />
      </div>
    </section>
  );
}
