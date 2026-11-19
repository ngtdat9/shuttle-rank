import { CardsSkeleton } from "@/components/loading-skeleton";

export default function Loading() {
  return <CardsSkeleton count={4} className="lg:grid-cols-2" />;
}
