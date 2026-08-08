import { Skeleton } from "@/components/ui/skeleton";

export function MovieListSkeleton() {
  return (
    <div className="space-y-5">
      {[0, 1, 2].map((i) => (
        <div key={i} className="surface-card flex flex-col gap-5 p-4 sm:flex-row sm:p-5">
          <Skeleton className="aspect-2/3 w-full rounded-lg sm:w-40" />
          <div className="flex-1 space-y-3">
            <Skeleton className="h-7 w-2/3" />
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-5/6" />
            <div className="flex gap-2 pt-3">
              <Skeleton className="h-16 w-28 rounded-lg" />
              <Skeleton className="h-16 w-28 rounded-lg" />
              <Skeleton className="h-16 w-28 rounded-lg" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function SeatMapSkeleton() {
  return (
    <div className="surface-card px-4 py-10">
      <Skeleton className="mx-auto h-3 w-full max-w-md rounded-full" />
      <Skeleton className="mx-auto mt-4 h-3 w-24" />
      <div className="mt-10 space-y-2">
        {Array.from({ length: 7 }).map((_, r) => (
          <div key={r} className="flex justify-center gap-2">
            {Array.from({ length: 10 }).map((_, c) => (
              <Skeleton key={c} className="h-9 w-9 rounded-[7px]" />
            ))}
          </div>
        ))}
      </div>
      <div className="mt-8 flex justify-center gap-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-4 w-20" />
        ))}
      </div>
    </div>
  );
}
