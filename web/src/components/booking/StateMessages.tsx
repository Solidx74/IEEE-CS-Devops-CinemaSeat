import { AlertTriangle, Popcorn } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="surface-card mx-auto max-w-md p-8 text-center"
    >
      <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-urgent/15">
        <AlertTriangle className="h-5 w-5 text-urgent" />
      </div>
      <h2 className="mt-4 font-display text-xl font-semibold">{title}</h2>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{message}</p>
      {onRetry && (
        <Button className="mt-5" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: { label: string; onClick: () => void };
}) {
  return (
    <div className="surface-card vignette mx-auto max-w-md p-10 text-center">
      <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-gold/12">
        <Popcorn className="h-6 w-6 text-gold" />
      </div>
      <h2 className="mt-4 font-display text-xl font-semibold">{title}</h2>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{message}</p>
      {action && (
        <Button variant="secondary" className="mt-5" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
