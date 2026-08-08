import { Star } from "lucide-react";
import { formatDuration, formatMoney } from "@/lib/format";
import type { CatalogMovie } from "@/lib/featured-movies";
import type { Movie, Showtime } from "@/types/booking";

interface LatestReleasesProps {
  movies: CatalogMovie[];
  onSelectShowtime: (movie: Movie, showtime: Showtime) => void;
}

export function LatestReleases({ movies, onSelectShowtime }: LatestReleasesProps) {
  if (movies.length === 0) return null;

  return (
    <section aria-labelledby="latest-heading" className="space-y-4">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-[11px] uppercase tracking-[0.24em] text-gold">
            Just released
          </p>
          <h2 id="latest-heading" className="mt-1 font-display text-xl font-semibold sm:text-2xl">
            Latest movies
          </h2>
        </div>
        <p className="hidden text-xs text-muted-foreground sm:block">
          Swipe for more →
        </p>
      </div>

      <div className="-mx-4 flex snap-x snap-mandatory gap-4 overflow-x-auto px-4 pb-2 sm:mx-0 sm:px-0">
        {movies.map((m) => {
          const first = m.showtimes[0];
          return (
            <button
              key={m.id}
              type="button"
              disabled={!first}
              onClick={() => first && onSelectShowtime(m, first)}
              className="surface-card group w-40 shrink-0 snap-start overflow-hidden p-0 text-left transition-transform hover:-translate-y-1 disabled:opacity-60 sm:w-44"
            >
              <div className="relative aspect-2/3 w-full overflow-hidden bg-secondary">
                <img
                  src={m.poster_url}
                  alt={`${m.title} poster`}
                  width={683}
                  height={1024}
                  loading="lazy"
                  className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                />
                <span className="absolute left-2 top-2 flex items-center gap-1 rounded-full bg-background/80 px-2 py-0.5 text-[10px] text-gold backdrop-blur">
                  <Star className="h-3 w-3 fill-gold text-gold" />
                  {m.rating.toFixed(1)}
                </span>
              </div>
              <div className="p-3">
                <h3 className="truncate font-display text-sm font-semibold">
                  {m.title}
                </h3>
                <p className="mt-1 truncate text-[11px] text-muted-foreground">
                  {m.genre}
                </p>
                <p className="mt-1.5 text-[11px] text-muted-foreground">
                  {formatDuration(m.duration_minutes)}
                  {first && ` · from ${formatMoney(first.price)}`}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
