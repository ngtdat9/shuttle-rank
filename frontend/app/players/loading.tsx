import { CardsSkeleton } from "@/components/loading-skeleton";

export default function Loading() {
  return <CardsSkeleton count={6} className="md:grid-cols-2 lg:grid-cols-3" />;
}
