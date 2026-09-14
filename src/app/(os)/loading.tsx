import { Skeleton } from "@/components/ui/skeleton";

// A route-level fallback keeps every workspace surface responsive during navigation.
export default function WorkspaceLoading() {
  return (
    <div className="mx-auto w-full max-w-6xl space-y-7 px-4 py-7 sm:px-6 sm:py-10 lg:px-10" aria-busy="true" aria-label="Loading workspace">
      <div className="space-y-3">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-9 w-56 max-w-full" />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Skeleton className="h-44 lg:col-span-2" />
        <Skeleton className="h-44" />
      </div>
      <div className="space-y-3 rounded-2xl border border-stone-200/70 bg-white p-4 sm:p-5">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-4/5" />
      </div>
    </div>
  );
}
