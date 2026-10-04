import { Skeleton } from "./Skeleton";

export function PageLoader() {
  return (
    <div className="space-y-5 p-6">
      <Skeleton className="h-10 w-80" />
      <div className="grid gap-4 md:grid-cols-3">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
      <Skeleton className="h-96" />
    </div>
  );
}
