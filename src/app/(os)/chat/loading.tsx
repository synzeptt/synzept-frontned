import { Skeleton } from "@/components/ui/skeleton";

export default function ChatLoading() {
  return (
    <div className="flex h-full min-h-0">
      <aside className="hidden w-[292px] shrink-0 border-r border-border bg-white p-4 lg:block">
        <Skeleton className="h-9 rounded-md" />
        <div className="mt-5 space-y-2">
          <Skeleton className="h-16 rounded-md" />
          <Skeleton className="h-16 rounded-md" />
          <Skeleton className="h-16 rounded-md" />
        </div>
      </aside>
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="min-h-16 border-b border-border bg-white/80 px-4 py-3 md:px-6">
          <Skeleton className="h-4 w-24 rounded-md" />
          <Skeleton className="mt-2 h-5 w-48 rounded-md" />
        </header>
        <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-5 px-4 py-8 md:px-6">
          <Skeleton className="h-24 w-3/4 rounded-xl" />
          <Skeleton className="ml-auto h-16 w-2/3 rounded-xl" />
          <Skeleton className="h-32 w-4/5 rounded-xl" />
        </div>
      </section>
    </div>
  );
}
