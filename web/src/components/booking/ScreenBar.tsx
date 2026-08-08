export function ScreenBar() {
  return (
    <div className="relative mx-auto mb-10 w-full max-w-md">
      <div
        aria-hidden
        className="absolute -top-4 left-1/2 h-24 w-[120%] -translate-x-1/2 rounded-[100%] bg-gold/18 blur-2xl"
      />
      <div className="relative h-3 w-full rounded-[100%] bg-linear-to-r from-transparent via-gold to-transparent opacity-90" />
      <p className="relative mt-3 text-center font-display text-[11px] uppercase tracking-[0.5em] text-gold/80">
        Screen
      </p>
    </div>
  );
}
