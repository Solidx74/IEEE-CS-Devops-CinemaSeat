import { Button } from "@/components/ui/button";
import { formatDateTime, formatMoney } from "@/lib/format";
import type { Payment, SeatMapResponse, Seat } from "@/types/booking";

interface TicketStubProps {
  payment: Payment;
  seatMap: SeatMapResponse;
  seat: Seat;
  email: string;
  onStartOver: () => void;
}

export function TicketStub({
  payment,
  seatMap,
  seat,
  email,
  onStartOver,
}: TicketStubProps) {
  return (
    <div className="animate-rise mx-auto max-w-md">
      <p className="mb-4 text-center text-[11px] uppercase tracking-[0.28em] text-success">
        Booking confirmed
      </p>

      <div className="relative overflow-hidden rounded-2xl bg-linear-to-b from-surface-2 to-surface shadow-glow-gold">
        <div className="h-1 w-full bg-linear-to-r from-transparent via-gold to-transparent" />

        <div className="p-6">
          <p className="text-[10px] uppercase tracking-[0.3em] text-gold">CinemaSeat</p>
          <h2 className="mt-2 font-display text-2xl font-semibold leading-tight">
            {seatMap.movie_title}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">{seatMap.theatre_name}</p>

          <dl className="mt-6 grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                Showtime
              </dt>
              <dd className="mt-1 font-medium">{formatDateTime(seatMap.starts_at)}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                Seat
              </dt>
              <dd className="mt-1 font-display text-lg font-semibold text-gold">
                {seat.row_label}
                {seat.seat_number}
                <span className="ml-2 align-middle text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                  {seat.seat_type}
                </span>
              </dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                Paid
              </dt>
              <dd className="mt-1 font-medium">{formatMoney(payment.amount)}</dd>
            </div>
            <div className="min-w-0">
              <dt className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                Email
              </dt>
              <dd className="mt-1 truncate font-medium">{email}</dd>
            </div>
          </dl>
        </div>

        {/* Perforation */}
        <div className="relative flex items-center">
          <span className="absolute -left-3 h-6 w-6 rounded-full bg-background" />
          <span className="mx-6 h-px flex-1 border-t border-dashed border-border" />
          <span className="absolute -right-3 h-6 w-6 rounded-full bg-background" />
        </div>

        <div className="flex items-center gap-5 p-6">
          <div
            aria-hidden
            className="grid h-24 w-24 shrink-0 grid-cols-6 gap-0.5 rounded-lg bg-foreground p-1.5"
          >
            {Array.from({ length: 36 }).map((_, i) => (
              <span
                key={i}
                className={
                  (i * 7 + (i % 5)) % 3 === 0 ? "rounded-[1px] bg-background" : ""
                }
              />
            ))}
          </div>
          <div className="min-w-0">
            <p className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
              Booking reference
            </p>
            <p className="mt-1 break-all font-mono text-lg font-semibold tracking-wider text-gold">
              {payment.booking_ref}
            </p>
            <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
              Show this at the counter to collect your ticket.
            </p>
          </div>
        </div>
      </div>

      <Button variant="outline" className="mt-6 w-full" size="lg" onClick={onStartOver}>
        Book another seat
      </Button>
    </div>
  );
}
