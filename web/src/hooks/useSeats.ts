import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

/** Polls the seat map so seats update live while the user is picking. */
export function useSeats(showtimeId: string | null, active: boolean) {
  return useQuery({
    queryKey: ["seats", showtimeId],
    queryFn: () => api.getSeats(showtimeId as string),
    enabled: Boolean(showtimeId),
    refetchInterval: active ? 4000 : false,
    refetchOnWindowFocus: true,
  });
}
