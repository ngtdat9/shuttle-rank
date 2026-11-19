import { CardsSkeleton } from "@/components/loading-skeleton";

export default function Loading() {
  return <CardsSkeleton count={1} className="mx-auto max-w-[720px] sm:grid-cols-1" />;
}
