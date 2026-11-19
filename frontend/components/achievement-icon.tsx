import {
  Award,
  Crown,
  Flame,
  Medal,
  Shield,
  Star,
  Swords,
  Target,
  Trophy,
  Zap,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

const ICONS: Record<string, LucideIcon> = {
  award: Award,
  crown: Crown,
  flame: Flame,
  medal: Medal,
  shield: Shield,
  star: Star,
  swords: Swords,
  target: Target,
  trophy: Trophy,
  zap: Zap,
};

export function AchievementIcon({
  name,
  className,
}: {
  name: string;
  className?: string;
}) {
  const Icon = ICONS[name.trim().toLowerCase()] ?? Award;
  return <Icon className={cn("size-4", className)} strokeWidth={1.75} aria-hidden />;
}
