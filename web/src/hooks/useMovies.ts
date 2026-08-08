import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Movie } from "@/types/booking";

export function useMovies() {
  return useQuery<Movie[]>({
    queryKey: ["movies"],
    queryFn: () => api.getMovies(),
    retry: false,
    staleTime: 30_000,
  });
}
