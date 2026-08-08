import { Loader2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { describePayment, formatMoney, TERMINAL_PENDING } from "@/lib/format";
import type { Payment } from "@/types/booking";

interface PaymentStatusProps {
  payment: Payment | undefined;
  isLoading: boolean;
  onStartOver: () => void;
}

export function PaymentStatus({ payment, isLoading, onStartOver }: PaymentStatusProps) {
  const status = payment?.status ?? "INITIATING";
  const pending = isLoading || TERMINAL_PENDING.includes(status);
  const copy = describePayment(status);

  return (
    <section className="surface-card animate-rise mx-auto max-w-lg p-8 text-center">
      <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-secondary">
        {pending ? (
          <Loader2 className="h-6 w-6 animate-spin text-gold" />
        ) : (
          <XCircle className="h-6 w-6 text-urgent" />
        )}
      </div>

      <h2 className="mt-5 font-display text-2xl font-semibold">{copy.title}</h2>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{copy.body}</p>

      <dl className="mt-6 space-y-2 rounded-lg bg-background/40 p-4 text-left text-sm">
        {payment?.booking_ref && (
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Booking ref</dt>
            <dd className="font-mono">{payment.booking_ref}</dd>
          </div>
        )}
        {payment?.amount != null && (
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Amount</dt>
            <dd>{formatMoney(payment.amount)}</dd>
          </div>
        )}
        <div className="flex justify-between gap-4">
          <dt className="text-muted-foreground">Status</dt>
          <dd className="font-mono text-xs uppercase tracking-wider">{status}</dd>
        </div>
      </dl>

      {!pending && (
        <Button className="mt-6 w-full" size="lg" onClick={onStartOver}>
          Start a new booking
        </Button>
      )}
    </section>
  );
}
