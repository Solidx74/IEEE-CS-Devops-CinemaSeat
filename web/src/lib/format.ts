export const CURRENCY = "৳";

export function formatMoney(amount: number): string {
  return `${CURRENCY}${Number(amount).toLocaleString("en-US", {
    maximumFractionDigits: 2,
  })}`;
}

export function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString([], {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const mm = Math.floor(s / 60)
    .toString()
    .padStart(2, "0");
  const ss = (s % 60).toString().padStart(2, "0");
  return `${mm}:${ss}`;
}

const PAYMENT_COPY: Record<string, { title: string; body: string }> = {
  PENDING: {
    title: "Payment pending",
    body: "We're waiting for the gateway to confirm your payment.",
  },
  INITIATING: {
    title: "Contacting the payment gateway",
    body: "Hang tight — this usually takes a few seconds.",
  },
  SUCCEEDED: {
    title: "Payment successful",
    body: "Your seat is confirmed.",
  },
  FAILED: {
    title: "Payment failed",
    body: "The gateway declined the payment. Nothing was charged.",
  },
  INITIATION_FAILED: {
    title: "Couldn't start the payment",
    body: "We couldn't reach the payment gateway. Please try again.",
  },
  SUCCEEDED_NO_HOLD: {
    title: "Payment went through, but the hold expired",
    body: "Your seat hold ran out before payment landed. A refund is being arranged.",
  },
  CONFLICT_REFUND_REQUIRED: {
    title: "Seat was taken by someone else",
    body: "Another customer booked this seat first. A refund is required and being arranged.",
  },
  REFUNDED: {
    title: "Payment refunded",
    body: "This payment has been refunded. You can start a new booking.",
  },
};

export function describePayment(status: string) {
  return (
    PAYMENT_COPY[status] ?? {
      title: "Unknown payment status",
      body: `The gateway returned "${status}". Please start over or contact support.`,
    }
  );
}

export const TERMINAL_PENDING = ["PENDING", "INITIATING"];
