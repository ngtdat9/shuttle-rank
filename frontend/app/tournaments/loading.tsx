import { CardsSkeleton } from "@/components/loading-skeleton";

export default function Loading() {
  return <CardsSkeleton count={4} className="md:grid-cols-2" />;
}
