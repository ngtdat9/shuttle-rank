import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

const AVATAR_COLORS = [
  "#2f6b4f",
  "#1f7a76",
  "#3e5c8a",
  "#6b5344",
  "#5a3e6b",
  "#3f5e3a",
  "#6b3e45",
  "#3a5560",
];

type PlayerAvatarProps = {
  name: string;
  imageUrl?: string | null;
  size?: "sm" | "md" | "lg";
  /** Bright fill (dark initials) instead of the name-derived dark tone. */
  accent?: string;
  className?: string;
};

export function colorFromName(name: string): string {
  let hash = 0;
  for (const char of name) {
    hash = (hash * 31 + char.charCodeAt(0)) % 2147483647;
  }
  const index = Math.abs(hash) % AVATAR_COLORS.length;
  return AVATAR_COLORS[index] ?? AVATAR_COLORS[0];
}

export function initialsFromName(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return "?";
  }
  if (parts.length === 1) {
    return parts[0]!.slice(0, 2).toUpperCase();
  }
  const first = parts[0]?.[0] ?? "";
  const second = parts[1]?.[0] ?? "";
  return `${first}${second}`.toUpperCase();
}

const SIZE_MAP = {
  sm: "sm",
  md: "default",
  lg: "lg",
} as const;

export function PlayerAvatar({
  name,
  imageUrl,
  size = "md",
  accent,
  className,
}: PlayerAvatarProps) {
  const image = imageUrl?.trim();

  return (
    <Avatar size={SIZE_MAP[size]} className={cn(className)} aria-label={name}>
      {image ? <AvatarImage src={image} alt="" /> : null}
      <AvatarFallback
        aria-hidden
        style={
          accent
            ? { backgroundColor: accent, color: "#0b0f0c" }
            : { backgroundColor: colorFromName(name), color: "#f5f7f5" }
        }
        className="font-medium"
      >
        {initialsFromName(name)}
      </AvatarFallback>
    </Avatar>
  );
}
