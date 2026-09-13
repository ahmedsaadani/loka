"use client";

import { CalendarDays, Users } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiRequestError } from "@/lib/api/client";
import { useAuth } from "@/lib/api/auth-context";
import type { BookingRequest, PricingPlan, Quote, RentalMode } from "@/lib/api/types";
import { t } from "@/lib/i18n";
import {
  addDays,
  addMonths,
  cn,
  formatEur,
  formatTnd,
  RENTAL_MODE_LABEL,
  RENTAL_MODE_TITLE,
  toIsoDate,
} from "@/lib/utils";

import { AvailabilityCalendar } from "./AvailabilityCalendar";

interface Props {
  slug: string;
  plans: PricingPlan[];
  maxGuests: number;
  ownerMode?: boolean;
  className?: string;
}

const ORDER: RentalMode[] = ["nightly", "monthly", "yearly"];

export function BookingBox({ slug, plans, maxGuests, className }: Props) {
  const router = useRouter();
  const { status } = useAuth();
  const modes = ORDER.filter((m) => plans.some((p) => p.rental_mode === m && p.is_active));
  const [mode, setMode] = useState<RentalMode>(
    modes.includes("monthly") ? "monthly" : (modes[0] ?? "monthly"),
  );
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [guests, setGuests] = useState(1);
  const [message, setMessage] = useState("");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const plan = plans.find((p) => p.rental_mode === mode && p.is_active);
  const today = useMemo(() => toIsoDate(new Date()), []);

  // Pour les modes mensuel / annuel, la fin est calculée depuis le début.
  useEffect(() => {
    if (!start) return;
    if (mode === "yearly") setEnd(toIsoDate(addMonths(new Date(start), 12)));
    else if (mode === "monthly" && (!end || end <= start))
      setEnd(toIsoDate(addMonths(new Date(start), Math.max(1, plan?.min_duration ?? 1))));
    else if (mode === "nightly" && (!end || end <= start))
      setEnd(toIsoDate(addDays(new Date(start), Math.max(1, plan?.min_duration ?? 1))));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, start]);

  useEffect(() => {
    if (!start || !end || end <= start) {
      setQuote(null);
      setQuoteError(null);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    api
      .get<Quote>(
        `/listings/properties/${slug}/quote/`,
        { rental_mode: mode, start, end },
        controller.signal,
      )
      .then((q) => {
        setQuote(q);
        setQuoteError(q.available ? null : t.listing.unavailable);
      })
      .catch((error: unknown) => {
        setQuote(null);
        setQuoteError(error instanceof ApiRequestError ? error.message : t.common.error);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [slug, mode, start, end]);

  async function submit() {
    if (!quote?.available) return;
    setSubmitting(true);
    try {
      const request = await api.post<BookingRequest>("/bookings/requests/", {
        property: slug,
        rental_mode: mode,
        start_date: start,
        end_date: end,
        guests,
        message,
      });
      toast.success("Demande envoyée. L'hôte a 48 h pour répondre.");
      router.push(`/compte/demandes/${request.public_id}`);
    } catch (error) {
      toast.error(error instanceof ApiRequestError ? error.message : t.common.error);
    } finally {
      setSubmitting(false);
    }
  }

  const nextUrl = `/logement/${slug}`;
  const canSubmit = Boolean(quote?.available) && guests >= 1 && guests <= maxGuests;

  return (
    <div
      className={cn("rounded-2xl border bg-card p-4 shadow-card md:p-5", className)}
      data-testid="booking-box"
    >
      {plan ? (
        <p className="text-2xl font-semibold">
          {formatTnd(plan.price)}
          <span className="text-sm font-normal text-muted-foreground">
            {" "}
            / {RENTAL_MODE_LABEL[plan.rental_mode]}
          </span>
        </p>
      ) : (
        <p className="text-muted-foreground">Prix sur demande</p>
      )}

      {modes.length > 1 && (
        <Tabs value={mode} onValueChange={(v) => setMode(v as RentalMode)} className="mt-3">
          <TabsList
            className="grid w-full"
            style={{ gridTemplateColumns: `repeat(${modes.length}, minmax(0, 1fr))` }}
          >
            {modes.map((m) => (
              <TabsTrigger key={m} value={m} data-testid={`booking-mode-${m}`}>
                {RENTAL_MODE_TITLE[m]}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      )}

      <div className="mt-4 grid grid-cols-2 gap-2">
        <div>
          <Label htmlFor="bb-start">{t.search.from}</Label>
          <Input
            id="bb-start"
            type="date"
            min={today}
            value={start}
            onChange={(e) => setStart(e.target.value)}
            data-testid="booking-start"
          />
        </div>
        <div>
          <Label htmlFor="bb-end">{t.search.to}</Label>
          <Input
            id="bb-end"
            type="date"
            min={start || today}
            value={end}
            disabled={mode === "yearly"}
            onChange={(e) => setEnd(e.target.value)}
            data-testid="booking-end"
          />
        </div>
      </div>
      <Button
        variant="link"
        size="sm"
        className="mt-1 h-auto px-0"
        onClick={() => setCalendarOpen(true)}
      >
        <CalendarDays /> {t.listing.calendar}
      </Button>

      <div className="mt-2">
        <Label htmlFor="bb-guests">
          <Users className="mr-1 inline h-4 w-4" />
          {t.search.guests} (max {maxGuests})
        </Label>
        <Input
          id="bb-guests"
          type="number"
          min={1}
          max={maxGuests}
          value={guests}
          onChange={(e) => setGuests(Number(e.target.value))}
          data-testid="booking-guests"
        />
      </div>

      <div className="mt-4 space-y-1 text-sm" aria-live="polite">
        {loading && <p className="text-muted-foreground">{t.common.loading}</p>}
        {quoteError && <p className="text-destructive">{quoteError}</p>}
        {quote && !quoteError && (
          <dl className="space-y-1" data-testid="quote">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">
                {formatTnd(quote.unit_price)} × {quote.units} {quote.unit_label}
                {quote.units > 1 && quote.unit_label === "nuit" ? "s" : ""}
              </dt>
              <dd>{formatTnd(quote.subtotal)}</dd>
            </div>
            {quote.fee_payer === "traveler" ? (
              <div className="flex justify-between">
                <dt className="text-muted-foreground">{t.listing.fees}</dt>
                <dd>{formatTnd(quote.fee)}</dd>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">{t.listing.hostFeesNote}</p>
            )}
            <div className="flex justify-between border-t pt-1 font-semibold">
              <dt>{t.listing.total}</dt>
              <dd>
                {formatTnd(quote.total)}{" "}
                <span className="text-xs font-normal text-muted-foreground">
                  ≈ {formatEur(quote.total_eur)}
                </span>
              </dd>
            </div>
            <div className="flex justify-between text-primary">
              <dt>{t.listing.depositDue}</dt>
              <dd>{formatTnd(quote.deposit)}</dd>
            </div>
            {Number(quote.security_deposit) > 0 && (
              <p className="text-xs text-muted-foreground">
                Caution : {formatTnd(quote.security_deposit)}, versée à l&apos;hôte à l&apos;entrée.
              </p>
            )}
          </dl>
        )}
      </div>

      {status === "authenticated" ? (
        <>
          <div className="mt-3">
            <Label htmlFor="bb-message">Message à l&apos;hôte ({t.common.optional})</Label>
            <Textarea
              id="bb-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              maxLength={2000}
              rows={3}
            />
          </div>
          <Button
            className="mt-4 w-full"
            size="lg"
            disabled={!canSubmit || submitting}
            onClick={submit}
            data-testid="booking-submit"
          >
            {t.listing.book}
          </Button>
        </>
      ) : (
        <Button className="mt-4 w-full" size="lg" asChild>
          <Link href={`/connexion?next=${encodeURIComponent(nextUrl)}`}>
            {status === "loading" ? t.common.loading : t.listing.loginToBook}
          </Link>
        </Button>
      )}
      <p className="mt-2 text-center text-xs text-muted-foreground">{t.listing.bookHint}</p>

      <Dialog open={calendarOpen} onOpenChange={setCalendarOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t.listing.calendar}</DialogTitle>
            <DialogDescription>
              Sélectionnez une date de début puis une date de fin.
            </DialogDescription>
          </DialogHeader>
          <AvailabilityCalendar
            slug={slug}
            selection={start && end ? { start, end } : undefined}
            onSelect={({ start: s, end: e }) => {
              setStart(s);
              setEnd(e);
              setCalendarOpen(false);
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
