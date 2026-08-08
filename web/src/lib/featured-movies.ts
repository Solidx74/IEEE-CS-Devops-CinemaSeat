import type { Movie } from "@/types/booking";

import bannerOrbital from "@/assets/banner-orbital.jpg";
import bannerNeon from "@/assets/banner-neon.jpg";
import bannerDunes from "@/assets/banner-dunes.jpg";
import posterOrbital from "@/assets/poster-orbital.jpg";
import posterNeon from "@/assets/poster-neon.jpg";
import posterDunes from "@/assets/poster-dunes.jpg";

export interface CatalogMovie extends Movie {
  genre: string;
  rating: number;
  certificate: string;
  released_on: string;
  banner_url?: string;
  tagline?: string;
}

type Presentation = {
  poster_url: string;
  banner_url: string;
  genre: string;
  rating: number;
  certificate: string;
  released_on: string;
  tagline: string;
};

const PRESENTATIONS: Presentation[] = [
  {
    poster_url: posterOrbital,
    banner_url: bannerOrbital,
    genre: "Sci-Fi · Epic",
    rating: 8.7,
    certificate: "PG-13",
    released_on: "2026-08-07",
    tagline: "One station. One sunrise left.",
  },
  {
    poster_url: posterNeon,
    banner_url: bannerNeon,
    genre: "Drama · Mystery",
    rating: 8.2,
    certificate: "PG-13",
    released_on: "2026-08-01",
    tagline: "Every signal leaves a trace.",
  },
  {
    poster_url: posterDunes,
    banner_url: bannerDunes,
    genre: "Thriller · Adventure",
    rating: 7.9,
    certificate: "PG-13",
    released_on: "2026-07-25",
    tagline: "The message was meant for tomorrow.",
  },
];

/**
 * Adds presentation-only metadata to real catalog records. IDs, showtimes,
 * prices, theatres, titles, and descriptions always remain API-owned.
 */
export function decorateCatalogMovies(movies: Movie[]): CatalogMovie[] {
  return movies.map((movie, index) => {
    const presentation = PRESENTATIONS[index % PRESENTATIONS.length]!;
    return {
      ...movie,
      poster_url: movie.poster_url || presentation.poster_url,
      banner_url: presentation.banner_url,
      genre: presentation.genre,
      rating: presentation.rating,
      certificate: presentation.certificate,
      released_on: presentation.released_on,
      tagline: presentation.tagline,
    };
  });
}
