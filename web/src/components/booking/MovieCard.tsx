import { Clock, Film } from "lucide-react";
import { formatDuration, formatMoney, formatTime } from "@/lib/format";
import type { Movie, Showtime } from "@/types/booking";
import { ShowtimeChip } from "./ShowtimeChip";

interface MovieCardProps {
  movie: Movie;
  onSelectShowtime: (movie: Movie, showtime: Showtime) => void;
}

export function MovieCard({ movie, onSelectShowtime }: MovieCardProps) {
  return (
    <article className="surface-card animate-rise group overflow-hidden">
      <div className="flex flex-col gap-5 p-4 sm:flex-row sm:p-5">
        <div className="relative w-full shrink-0 overflow-hidden rounded-lg bg-secondary sm:w-40">
          <div className="aspect-2/3 w-full">
            {movie.poster_url ? (
              <img
                src={movie.poster_url}
                alt={`${movie.title} poster`}
                loading="lazy"
                className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
              />
            ) : (
              <div className="grid h-full w-full place-items-center text-muted-foreground">
                <Film className="h-8 w-8" />
              </div>
            )}
          </div>
        </div>

        <div className="flex min-w-0 flex-1 flex-col">
          <h3 className="font-display text-xl font-semibold text-foreground sm:text-2xl">
            {movie.title}
          </h3>
          <p className="mt-1 flex items-center gap-1.5 text-xs uppercase tracking-[0.14em] text-gold">
            <Clock className="h-3.5 w-3.5" />
            {formatDuration(movie.duration_minutes)}
          </p>
          <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-muted-foreground">
            {movie.description}
          </p>

          <div className="mt-5">
            <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Showtimes
            </p>
            {movie.showtimes.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No showtimes scheduled yet.
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {movie.showtimes.map((s) => (
                  <ShowtimeChip
                    key={s.id}
                    theatre={s.theatre_name}
                    time={formatTime(s.starts_at)}
                    price={formatMoney(s.price)}
                    onClick={() => onSelectShowtime(movie, s)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
