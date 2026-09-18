"use client";

import Link from "next/link";
import { Star } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { api, ApiRequestError } from "@/lib/api/client";
import { useApi } from "@/lib/api/hooks";
import type { MyReview, ReviewableBooking } from "@/lib/api/types";
import { formatDate } from "@/lib/utils";

export default function MyReviewsPage() {
  const pending = useApi<ReviewableBooking[]>("/reviews/pending/");
  const mine = useApi<MyReview[]>("/reviews/mine/");

  async function refreshAll() {
    await Promise.all([pending.refetch(), mine.refetch()]);
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl md:text-3xl">Mes avis</h1>
        <p className="text-muted-foreground">
          Partagez votre expérience après un séjour terminé pour aider les autres voyageurs.
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg">À évaluer</h2>
        {pending.loading && <p className="text-sm text-muted-foreground">Chargement…</p>}
        {!pending.loading && (pending.data?.length ?? 0) === 0 && (
          <p className="text-sm text-muted-foreground">
            Aucun séjour à évaluer pour l&apos;instant. Vos avis apparaîtront ici une fois vos
            séjours terminés.
          </p>
        )}
        <ul className="space-y-3">
          {pending.data?.map((booking) => (
            <ReviewForm key={booking.booking} booking={booking} onDone={refreshAll} />
          ))}
        </ul>
      </section>

      {(mine.data?.length ?? 0) > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg">Avis publiés</h2>
          <ul className="space-y-3">
            {mine.data?.map((review) => (
              <li key={review.public_id} className="rounded-xl border bg-card p-4">
                <div className="flex items-center justify-between gap-2">
                  <Link
                    href={`/logement/${review.property_slug}`}
                    className="font-medium hover:underline"
                  >
                    {review.property_title}
                  </Link>
                  <StarRow value={review.rating} />
                </div>
                {review.comment && (
                  <p className="mt-2 text-sm text-foreground/90">{review.comment}</p>
                )}
                <p className="mt-2 text-xs text-muted-foreground">
                  {formatDate(review.created_at)}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function StarRow({ value }: { value: number }) {
  return (
    <span className="inline-flex" aria-label={`${value} sur 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          className={
            i <= value
              ? "h-4 w-4 fill-amber-400 text-amber-400"
              : "h-4 w-4 text-muted-foreground/30"
          }
        />
      ))}
    </span>
  );
}

function ReviewForm({ booking, onDone }: { booking: ReviewableBooking; onDone: () => void }) {
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (rating === 0) {
      setError("Choisissez une note.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/reviews/", { booking: booking.booking, rating, comment });
      onDone();
    } catch (e) {
      setError(e instanceof ApiRequestError ? e.message : "Envoi impossible.");
      setSubmitting(false);
    }
  }

  return (
    <li className="rounded-xl border bg-card p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-1">
        <Link href={`/logement/${booking.property_slug}`} className="font-medium hover:underline">
          {booking.property_title}
        </Link>
        <span className="text-xs text-muted-foreground">
          {booking.city} · {formatDate(booking.start_date)} – {formatDate(booking.end_date)}
        </span>
      </div>
      <div className="mt-3 flex items-center gap-1" role="radiogroup" aria-label="Note">
        {[1, 2, 3, 4, 5].map((i) => (
          <button
            key={i}
            type="button"
            role="radio"
            aria-checked={rating === i}
            aria-label={`${i} étoile${i > 1 ? "s" : ""}`}
            onClick={() => setRating(i)}
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(0)}
            className="p-0.5"
          >
            <Star
              className={
                i <= (hover || rating)
                  ? "h-6 w-6 fill-amber-400 text-amber-400"
                  : "h-6 w-6 text-muted-foreground/30"
              }
            />
          </button>
        ))}
      </div>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        maxLength={2000}
        rows={3}
        placeholder="Partagez votre expérience (facultatif)…"
        className="mt-3 w-full rounded-md border bg-background px-3 py-2 text-sm"
      />
      {error && (
        <p className="mt-1 text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      <Button onClick={submit} disabled={submitting} size="sm" className="mt-2">
        Publier mon avis
      </Button>
    </li>
  );
}
