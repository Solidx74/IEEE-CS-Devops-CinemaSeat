import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { ArrowLeft, Loader2, Lock, Ticket } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StepIndicator } from "@/components/booking/StepIndicator";
import { MovieCard } from "@/components/booking/MovieCard";
import { SeatMap } from "@/components/booking/SeatMap";
import { HoldTimer } from "@/components/booking/HoldTimer";
import { PaymentStatus } from "@/components/booking/PaymentStatus";
import { TicketStub } from "@/components/booking/TicketStub";
import { OtpDemoCard } from "@/components/booking/OtpDemoCard";
import { MovieListSkeleton, SeatMapSkeleton } from "@/components/booking/Skeletons";
import { EmptyState, ErrorState } from "@/components/booking/StateMessages";
import { HeroBanner } from "@/components/booking/HeroBanner";
import { LatestReleases } from "@/components/booking/LatestReleases";
import { decorateCatalogMovies } from "@/lib/featured-movies";

import { useMovies } from "@/hooks/useMovies";
import { useSeats } from "@/hooks/useSeats";
import { useCountdown } from "@/hooks/useCountdown";
import { usePaymentPolling } from "@/hooks/usePaymentPolling";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatMoney, TERMINAL_PENDING } from "@/lib/format";
import type { BookingStep, Hold, Movie, Seat, Showtime } from "@/types/booking";

const TITLE = "CinemaSeat — Book Cinema Seats in Seconds";
const DESCRIPTION =
  "Pick your movie, choose your seat on a live seat map, hold it, and pay — a premium cinema booking experience.";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: TITLE },
      { name: "description", content: DESCRIPTION },
      { property: "og:title", content: TITLE },
      { property: "og:description", content: DESCRIPTION },
    ],
  }),
  component: BookingPage,
});

function BookingPage() {
  const [step, setStep] = useState<BookingStep>("browse");
  const [movie, setMovie] = useState<Movie | null>(null);
  const [showtime, setShowtime] = useState<Showtime | null>(null);
  const [selectedSeat, setSelectedSeat] = useState<Seat | null>(null);
  const [email, setEmail] = useState("");
  const [hold, setHold] = useState<Hold | null>(null);
  const [holding, setHolding] = useState(false);
  const [paymentId, setPaymentId] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);

  const moviesQuery = useMovies();
  const seatsQuery = useSeats(showtime?.id ?? null, step === "seats");
  const paymentQuery = usePaymentPolling(paymentId);
  const remaining = useCountdown(hold?.expires_at ?? null);

  const payment = paymentQuery.data;
  const paymentPending =
    !payment || TERMINAL_PENDING.includes(payment.status);

  useEffect(() => {
    if (!payment) return;
    if (payment.status === "SUCCEEDED" && payment.booking_confirmed) {
      setStep("ticket");
    }
  }, [payment]);

  useEffect(() => {
    if (step !== "hold" || !hold) return;
    // Compare against the hold's own expiry: `remaining` is 0 on the first
    // render after the hold is created, before the countdown's first tick.
    
    if (Date.now() < new Date(hold.expires_at).getTime()) return;

    toast.error("Your hold expired", {
      description: "The seat has been released — please pick a seat again.",
    });
    setHold(null);
    setSelectedSeat(null);
    setStep("seats");
  }, [remaining, step, hold]);


  const reset = useCallback(() => {
    setStep("browse");
    setMovie(null);
    setShowtime(null);
    setSelectedSeat(null);
    setHold(null);
    setPaymentId(null);
    setPaying(false);
  }, []);

  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

  const handleSelectShowtime = (m: Movie, s: Showtime) => {
    setMovie(m);
    setShowtime(s);
    setSelectedSeat(null);
    setStep("seats");
  };

  const handleSelectSeat = (seat: Seat) => {
    setSelectedSeat((prev) => (prev?.id === seat.id ? null : seat));
  };

  const handleHold = async () => {
    if (!showtime || !selectedSeat) return;
    setHolding(true);
    try {
      const res = await api.createHold(showtime.id, selectedSeat.id, email.trim());
      setHold(res);
      setStep("hold");
      toast.success(
        `Seat ${selectedSeat.row_label}${selectedSeat.seat_number} is yours for now`,
        { description: "Complete payment before the timer runs out." },
      );
    } catch (e) {
      const detail =
        e instanceof ApiError ? e.detail : "Couldn't hold that seat. Try again.";
      toast.error(
        e instanceof ApiError && e.status === 409
          ? "Seat is already held or booked"
          : "Couldn't hold that seat",
        { description: detail },
      );
      setSelectedSeat(null);
      void seatsQuery.refetch();
    } finally {
      setHolding(false);
    }
  };

  const handlePay = async () => {
    if (!hold) return;
    setPaying(true);
    setStep("pay");
    try {
      const res = await api.pay(hold.hold_id);
      setPaymentId(res.payment_id);
    } catch (e) {
      const detail =
        e instanceof ApiError ? e.detail : "Couldn't start the payment.";
      toast.error("Payment couldn't start", { description: detail });
      setPaying(false);
      setStep("hold");
    }
  };

  const seatMap = seatsQuery.data;
  const price = seatMap?.price ?? showtime?.price ?? 0;

  const seatLabel = useMemo(
    () =>
      selectedSeat
        ? `${selectedSeat.row_label}${selectedSeat.seat_number}`
        : null,
    [selectedSeat],
  );

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-border bg-background/85 backdrop-blur-lg">
        <div className="mx-auto max-w-5xl px-4 py-3 sm:px-6">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4">
            <button
              type="button"
              onClick={reset}
              className="flex min-w-0 items-center gap-2 text-left"
            >
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-gold/12 text-gold">
                <Ticket className="h-4.5 w-4.5" />
              </span>
              <span className="min-w-0">
                <span className="block truncate font-display text-base font-semibold tracking-tight">
                  Cinema<span className="text-gold">Seat</span>
                </span>
                <span className="hidden text-[10px] uppercase tracking-[0.22em] text-muted-foreground sm:block">
                  Premium cinema booking
                </span>
              </span>
            </button>
            {step !== "browse" && step !== "ticket" && (
              <Button
                variant="ghost"
                size="sm"
                onClick={step === "seats" ? reset : () => setStep("seats")}
                className="shrink-0 text-muted-foreground"
              >
                <ArrowLeft className="mr-1 h-4 w-4" />
                Back
              </Button>
            )}
          </div>
          <div className="mt-3">
            <StepIndicator current={step} />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
        {step === "browse" && (
          <BrowseScreen
            query={moviesQuery}
            onSelectShowtime={handleSelectShowtime}
          />
        )}

        {step === "seats" && (
          <div className="space-y-6">
            <div>
              <p className="text-[11px] uppercase tracking-[0.24em] text-gold">
                Choose your seat
              </p>
              <h1 className="mt-1 font-display text-2xl font-semibold sm:text-3xl">
                {seatMap?.movie_title ?? movie?.title}
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {(seatMap?.theatre_name ?? showtime?.theatre_name) ?? ""}
                {showtime && ` · ${formatDateTime(seatMap?.starts_at ?? showtime.starts_at)}`}
                {` · ${formatMoney(price)} per seat`}
              </p>
            </div>

            {seatsQuery.isPending && <SeatMapSkeleton />}

            {seatsQuery.isError && (
              <ErrorState
                title="Couldn't load the seat map"
                message={
                  seatsQuery.error instanceof ApiError
                    ? seatsQuery.error.detail
                    : "Please try again."
                }
                onRetry={() => void seatsQuery.refetch()}
              />
            )}

            {seatMap && seatMap.seats.length === 0 && (
              <EmptyState
                title="No seats in this hall yet"
                message="This showtime has no seats configured. Try a different showtime."
                action={{ label: "Back to movies", onClick: reset }}
              />
            )}

            {seatMap && seatMap.seats.length > 0 && (
              <>
                <SeatMap
                  seats={seatMap.seats}
                  selectedSeatId={selectedSeat?.id ?? null}
                  onSelect={handleSelectSeat}
                />

                <div className="surface-card p-5">
                  <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
                    <div className="min-w-0">
                      <Label htmlFor="email" className="text-xs text-muted-foreground">
                        Email for your ticket
                      </Label>
                      <Input
                        id="email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@example.com"
                        className="mt-1.5"
                      />
                      <p className="mt-2 text-xs text-muted-foreground">
                        {seatLabel ? (
                          <>
                            Seat <span className="text-gold">{seatLabel}</span> ·{" "}
                            {selectedSeat?.seat_type} · {formatMoney(price)}
                          </>
                        ) : (
                          "Pick an available seat above to continue."
                        )}
                      </p>
                    </div>
                    <Button
                      size="lg"
                      className="w-full shrink-0 sm:w-auto"
                      disabled={!selectedSeat || !emailValid || holding}
                      onClick={handleHold}
                    >
                      {holding ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Holding seat…
                        </>
                      ) : (
                        <>
                          <Lock className="mr-2 h-4 w-4" />
                          Hold seat
                        </>
                      )}
                    </Button>
                  </div>
                </div>

                <OtpDemoCard />
              </>
            )}
          </div>
        )}

        {step === "hold" && hold && selectedSeat && (
          <section className="surface-card vignette animate-rise mx-auto max-w-lg p-8 text-center">
            <p className="text-[11px] uppercase tracking-[0.24em] text-gold">
              Seat reserved — finish payment
            </p>
            <div className="mt-6 flex justify-center">
              <HoldTimer remaining={remaining} total={hold.ttl_seconds || 120} />
            </div>
            <p className="mt-5 text-sm text-muted-foreground">
              Seat{" "}
              <span className="font-display text-base font-semibold text-gold">
                {selectedSeat.row_label}
                {selectedSeat.seat_number}
              </span>{" "}
              releases automatically when the timer hits zero.
            </p>

            <dl className="mt-6 space-y-2 rounded-lg bg-background/40 p-4 text-left text-sm">
              <Row label="Movie" value={seatMap?.movie_title ?? movie?.title ?? "—"} />
              <Row
                label="Theatre"
                value={seatMap?.theatre_name ?? showtime?.theatre_name ?? "—"}
              />
              <Row label="Email" value={email} />
              <Row label="Total" value={formatMoney(price)} accent />
            </dl>

            <Button
              size="lg"
              className="mt-6 w-full"
              disabled={paying || remaining === 0}
              onClick={handlePay}
            >
              Pay {formatMoney(price)}
            </Button>
          </section>
        )}

        {step === "pay" && (
          <PaymentStatus
            payment={payment}
            isLoading={paymentQuery.isPending || paymentPending}
            onStartOver={reset}
          />
        )}

        {step === "ticket" && payment && seatMap && selectedSeat && (
          <TicketStub
            payment={payment}
            seatMap={seatMap}
            seat={selectedSeat}
            email={email}
            onStartOver={reset}
          />
        )}
      </main>

      <footer className="border-t border-border py-6 text-center text-xs text-muted-foreground">
        CinemaSeat · demo booking front-end
      </footer>
    </div>
  );
}

function Row({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={accent ? "font-semibold text-gold" : "truncate"}>{value}</dd>
    </div>
  );
}

function BrowseScreen({
  query,
  onSelectShowtime,
}: {
  query: ReturnType<typeof useMovies>;
  onSelectShowtime: (m: Movie, s: Showtime) => void;
}) {
  const catalogMovies = useMemo(
    () => decorateCatalogMovies(query.data ?? []),
    [query.data],
  );

  return (
    <div className="space-y-10">
      <HeroBanner movies={catalogMovies} onSelectShowtime={onSelectShowtime} />

      <div className="text-center">
        <h1 className="mx-auto max-w-2xl font-display text-2xl font-semibold leading-tight sm:text-4xl">
          The best seat in the house,{" "}
          <span className="text-gradient-gold">held just for you</span>
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground">
          Live seat availability, a two-minute hold while you pay, and your ticket
          in seconds.
        </p>
      </div>

      <LatestReleases movies={catalogMovies} onSelectShowtime={onSelectShowtime} />

      <div>
        <p className="text-[11px] uppercase tracking-[0.24em] text-gold">
          Now showing
        </p>
        <h2 className="mt-1 font-display text-xl font-semibold sm:text-2xl">
          All films &amp; showtimes
        </h2>
      </div>


      {query.isPending && <MovieListSkeleton />}

      {query.isError && (
        <ErrorState
          title="Couldn't load movies"
          message={
            query.error instanceof ApiError
              ? query.error.detail
              : "Please try again in a moment."
          }
          onRetry={() => void query.refetch()}
        />
      )}

      {query.data && query.data.length === 0 && (
        <EmptyState
          title="No films on the schedule"
          message="Our next season is being programmed. Check back shortly for showtimes."
        />
      )}

      {query.data && query.data.length > 0 && (
        <div className="space-y-5">
          {query.data.map((m) => (
            <MovieCard key={m.id} movie={m} onSelectShowtime={onSelectShowtime} />
          ))}
        </div>
      )}
    </div>
  );
}
