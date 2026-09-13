import Link from "next/link";

import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      className={cn("inline-flex items-center gap-2 text-xl font-bold tracking-tight", className)}
      aria-label="Loka, accueil"
    >
      <span
        className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-primary-foreground"
        aria-hidden="true"
      >
        <svg
          viewBox="0 0 24 24"
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M4 11.5 12 5l8 6.5" />
          <path d="M6.5 10.5V19h11v-8.5" />
          <path d="M10 19v-4.5h4V19" />
        </svg>
      </span>
      <span>Loka</span>
    </Link>
  );
}
