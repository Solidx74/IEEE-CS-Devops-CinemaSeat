import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { TERMINAL_PENDING } from "@/lib/format";

/** Polls a payment every second until it reaches a terminal status. */
export function usePaymentPolling(paymentId: string | null) {
  return useQuery({
    queryKey: ["payment", paymentId],
    queryFn: () => api.getPayment(paymentId as string),
    enabled: Boolean(paymentId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status) return 1000;
      return TERMINAL_PENDING.includes(status) ? 1000 : false;
    },
  });
}
