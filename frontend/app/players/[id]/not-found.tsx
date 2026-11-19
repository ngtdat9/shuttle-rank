import Link from "next/link";

import { textActionClass } from "@/components/club/styles";

export default function PlayerNotFound() {
  return (
    <div className="flex flex-col items-start gap-3">
      <h1 className="text-[28px] leading-[34px] font-semibold">This player isn&apos;t on Shuttle Rank.</h1>
      <Link href="/players" className={textActionClass}>
        All players
      </Link>
    </div>
  );
}
