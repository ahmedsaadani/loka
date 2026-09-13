"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";
import type { UnavailableRange } from "@/lib/api/types";
import { addDays, cn, toIsoDate } from "@/lib/utils";

interface Props {
  slug: string;
  months?: number;
  /** Sélection contrôlée (mode réservation). */
  selection?: { start: string; end: string };
  onSelect?: (range: { start: string; end: string }) => void;
  className?: string;
}

const WEEKDAYS = ["L", "M", "M", "J", "V", "S", "D"];
const MONTHS = [
  "janvier",
  "février",
  "mars",
  "avril",
  "mai",
  "juin",
  "juillet",
  "août",
  "septembre",
  "octobre",
  "novembre",
  "décembre",
];

function isBlocked(iso: string, ranges: UnavailableRange[]): boolean {
  return ranges.some((r) => iso >= r.start && iso < r.end);
}

export function useUnavailableRanges(slug: string, from: Date, days = 400) {
  const [ranges, setRanges] = useState<UnavailableRange[] | null>(null);
  const fromIso = toIsoDate(from);
  useEffect(() => {
    const controller = new AbortController();
    api
      .get<UnavailableRange[]>(
        `/listings/properties/${slug}/availability/`,
        { from: fromIso, to: toIsoDate(addDays(from, days)) },
        controller.signal,
      )
      .then(setRanges)
      .catch(() => setRanges([]));
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, fromIso, days]);
  return ranges;
}

export function AvailabilityCalendar({ slug, months = 2, selection, onSelect, className }: Props) {
  const today = useMemo(() => new Date(new Date().setHours(0, 0, 0, 0)), []);
  const [offset, setOffset] = useState(0);
  const [pending, setPending] = useState<string | null>(null);
  const ranges = useUnavailableRanges(slug, today);

  const monthsToRender = Array.from({ length: months }, (_, i) => {
    const d = new Date(today.getFullYear(), today.getMonth() + offset + i, 1);
    return d;
  });

  function handleClick(iso: string) {
    if (!onSelect) return;
    if (!pending || iso <= pending) {
      setPending(iso);
      return;
    }
    // Vérifie qu'aucun jour bloqué n'est dans [pending, iso)
    let cursor = new Date(pending);
    const end = new Date(iso);
    let ok = true;
    while (cursor < end) {
      if (isBlocked(toIsoDate(cursor), ranges ?? [])) {
        ok = false;
        break;
      }
      cursor = addDays(cursor, 1);
    }
    if (ok) onSelect({ start: pending, end: iso });
    setPending(ok ? null : iso);
  }

  const selStart = pending ?? selection?.start;
  const selEnd = pending ? undefined : selection?.end;

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setOffset((o) => Math.max(0, o - months))}
          disabled={offset === 0}
          aria-label="Mois précédents"
        >
          <ChevronLeft />
        </Button>
        <p className="text-sm text-muted-foreground">
          {onSelect
            ? pending
              ? "Choisissez la date de fin"
              : "Choisissez la date de début"
            : "Jours grisés : indisponibles"}
        </p>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setOffset((o) => Math.min(12, o + months))}
          aria-label="Mois suivants"
        >
          <ChevronRight />
        </Button>
      </div>
      <div className={cn("grid gap-6", months > 1 && "md:grid-cols-2")}>
        {monthsToRender.map((month) => (
          <MonthGrid
            key={month.toISOString()}
            month={month}
            today={today}
            ranges={ranges}
            selStart={selStart}
            selEnd={selEnd}
            onClick={onSelect ? handleClick : undefined}
          />
        ))}
      </div>
    </div>
  );
}

function MonthGrid({
  month,
  today,
  ranges,
  selStart,
  selEnd,
  onClick,
}: {
  month: Date;
  today: Date;
  ranges: UnavailableRange[] | null;
  selStart?: string;
  selEnd?: string;
  onClick?: (iso: string) => void;
}) {
  const first = new Date(month.getFullYear(), month.getMonth(), 1);
  const daysInMonth = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
  const leading = (first.getDay() + 6) % 7; // lundi = 0
  const cells: Array<Date | null> = [
    ...Array.from({ length: leading }, () => null),
    ...Array.from(
      { length: daysInMonth },
      (_, i) => new Date(month.getFullYear(), month.getMonth(), i + 1),
    ),
  ];

  return (
    <div>
      <p className="mb-2 text-sm font-semibold capitalize">
        {MONTHS[month.getMonth()]} {month.getFullYear()}
      </p>
      <div
        className="grid grid-cols-7 gap-1 text-center text-xs text-muted-foreground"
        aria-hidden="true"
      >
        {WEEKDAYS.map((d, i) => (
          <span key={i}>{d}</span>
        ))}
      </div>
      {ranges === null ? (
        <Skeleton className="mt-1 h-40 w-full" />
      ) : (
        <div className="mt-1 grid grid-cols-7 gap-1" role={onClick ? "grid" : undefined}>
          {cells.map((date, i) => {
            if (!date) return <span key={`e-${i}`} />;
            const iso = toIsoDate(date);
            const past = date < today;
            const blocked = isBlocked(iso, ranges);
            const disabled = past || blocked;
            const selected =
              Boolean(selStart && iso === selStart) || Boolean(selEnd && iso === selEnd);
            const inRange = Boolean(selStart && selEnd && iso > selStart && iso < selEnd);
            const Comp = onClick ? "button" : "span";
            return (
              <Comp
                key={iso}
                type={onClick ? "button" : undefined}
                onClick={onClick && !disabled ? () => onClick(iso) : undefined}
                disabled={onClick ? disabled : undefined}
                aria-label={`${date.getDate()} ${MONTHS[date.getMonth()]}${blocked ? ", indisponible" : ""}`}
                className={cn(
                  "grid h-9 place-items-center rounded-md text-sm",
                  disabled && "text-muted-foreground/50 line-through",
                  blocked && !past && "bg-muted",
                  !disabled && onClick && "hover:bg-accent",
                  selected && "bg-primary text-primary-foreground",
                  inRange && "bg-accent",
                )}
              >
                {date.getDate()}
              </Comp>
            );
          })}
        </div>
      )}
    </div>
  );
}
