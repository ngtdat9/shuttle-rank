import Link from "next/link";

import { textActionClass } from "@/components/club/styles";

export default function NotFound() {
  return (
    <div className="flex flex-col items-start gap-3">
      <h1 className="text-[28px] leading-[34px] font-semibold">This page isn&apos;t on Shuttle Rank.</h1>
      <Link href="/" className={textActionClass}>
        Back to the dashboard
      </Link>
    </div>
  );
}
