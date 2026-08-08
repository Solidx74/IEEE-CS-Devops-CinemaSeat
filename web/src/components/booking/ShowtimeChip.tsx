interface ShowtimeChipProps {
  theatre: string;
  time: string;
  price: string;
  onClick: () => void;
}

export function ShowtimeChip({ theatre, time, price, onClick }: ShowtimeChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group/chip rounded-lg border border-gold/25 bg-gold/5 px-3 py-2 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-gold/60 hover:bg-gold/10 hover:shadow-glow-gold focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span className="block font-display text-sm font-semibold text-foreground">
        {time}
      </span>
      <span className="mt-0.5 block truncate text-[11px] text-muted-foreground">
        {theatre}
      </span>
      <span className="mt-1 block text-xs font-medium text-gold">{price}</span>
    </button>
  );
}
