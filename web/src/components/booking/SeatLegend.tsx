const ITEMS = [
  { label: "Available", className: "bg-surface-2 border border-success/45" },
  { label: "Selected", className: "bg-gold border border-gold" },
  { label: "Premium", className: "bg-gold/12 border border-gold/70" },
  { label: "Held", className: "bg-urgent/15 border border-urgent/45" },
  { label: "Booked", className: "bg-secondary border border-border opacity-60" },
];

export function SeatLegend() {
  return (
    <ul className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2">
      {ITEMS.map((item) => (
        <li key={item.label} className="flex items-center gap-2">
          <span className={`h-4 w-4 rounded-[6px] ${item.className}`} />
          <span className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
            {item.label}
          </span>
        </li>
      ))}
    </ul>
  );
}
