import { useEffect, useState } from "react";
import { Play, Star, Ticket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatDuration, formatMoney, formatTime } from "@/lib/format";
import type { CatalogMovie } from "@/lib/featured-movies";
import type { Movie, Showtime } from "@/types/booking";

interface HeroBannerProps {
  movies: CatalogMovie[];
  onSelectShowtime: (movie: Movie, showtime: Showtime) => void;
}

export function HeroBanner({ movies, onSelectShowtime }: HeroBannerProps) {
  const [index, setIndex] = useState(0);
  const active = movies[index];

  useEffect(() => {
    if (movies.length < 2) return;
    const t = setInterval(
      () => setIndex((i) => (i + 1) % movies.length),
      7000,
    );
    return () => clearInterval(t);
  }, [movies.length]);

  if (!active) return null;
  const next = active.showtimes[0];

  return (
    <section
      aria-label="Popular now"
      className="surface-card relative overflow-hidden rounded-2xl"
    >
      <div className="relative aspect-16/10 w-full sm:aspect-21/9">
        {movies.map((m, i) => (
          <img
            key={m.id}
            src={m.banner_url}
            alt={`${m.title} banner`}
            width={1920}
            height={1080}
            loading={i === 0 ? "eager" : "lazy"}
            className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-1000 ${
              i === index ? "opacity-100" : "opacity-0"
            }`}
          />
        ))}
        <div
          aria-hidden
          className="absolute inset-0 bg-linear-to-t from-background via-background/70 to-background/10"
        />

        <div className="absolute inset-x-0 bottom-0 p-5 sm:p-8">
          <div className="flex flex-wrap items-center gap-3 text-[11px] uppercase tracking-[0.2em]">
            <span className="rounded-full bg-gold/15 px-2.5 py-1 text-gold">
              Popular now
            </span>
            <span className="flex items-center gap-1 text-foreground/80">
              <Star className="h-3.5 w-3.5 fill-gold text-gold" />
              {active.rating.toFixed(1)}
            </span>
            <span className="text-muted-foreground">{active.genre}</span>
            <span className="text-muted-foreground">
              {formatDuration(active.duration_minutes)}
            </span>
            <span className="rounded border border-border px-1.5 py-0.5 text-muted-foreground">
              {active.certificate}
            </span>
          </div>

          <h2 className="mt-3 max-w-2xl font-display text-2xl font-semibold leading-tight sm:text-4xl">
            {active.title}
          </h2>
          {active.tagline && (
            <p className="mt-1 font-display text-sm text-gold sm:text-base">
              {active.tagline}
            </p>
          )}
          <p className="mt-2 hidden max-w-xl text-sm leading-relaxed text-muted-foreground sm:line-clamp-2 sm:block">
            {active.description}
          </p>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            {next && (
              <Button
                size="lg"
                onClick={() => onSelectShowtime(active, next)}
                className="shrink-0"
              >
                <Ticket className="mr-2 h-4 w-4" />
                Book {formatTime(next.starts_at)} · {formatMoney(next.price)}
              </Button>
            )}
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Play className="h-3.5 w-3.5" />
              {active.showtimes.length} showtimes today
            </span>
          </div>

          <div className="mt-5 flex gap-2">
            {movies.map((m, i) => (
              <button
                key={m.id}
                type="button"
                aria-label={`Show ${m.title}`}
                aria-current={i === index}
                onClick={() => setIndex(i)}
                className={`h-1 rounded-full transition-all ${
                  i === index ? "w-8 bg-gold" : "w-4 bg-border hover:bg-muted"
                }`}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
