import { Star } from "lucide-react";

import { serverApi } from "@/lib/api/client";
import type { Paginated, Review } from "@/lib/api/types";
import { formatDate } from "@/lib/utils";

function Stars({ rating }: { rating: number }) {
  return (
    <span className="inline-flex" aria-label={`${rating} sur 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          className={
            i <= rating
              ? "h-4 w-4 fill-amber-400 text-amber-400"
              : "h-4 w-4 text-muted-foreground/30"
          }
        />
      ))}
    </span>
  );
}

/** Liste des avis publiés d'un bien (rendu serveur, données publiques en cache). */
export async function PropertyReviews({
  slug,
  rating,
  reviewCount,
}: {
  slug: string;
  rating: number | string | null;
  reviewCount: number;
}) {
  if (!rating || reviewCount === 0) return null;
  const page = await serverApi
    .get<Paginated<Review>>(
      "/reviews/",
      { property: slug, page_size: 6 },
      { revalidate: 300, tags: [`reviews:${slug}`] },
    )
    .catch(() => null);
  const reviews = page?.results ?? [];
  if (reviews.length === 0) return null;

  return (
    <section aria-labelledby="avis">
      <h2 id="avis" className="mb-4 flex items-center gap-2 text-lg">
        <Star className="h-5 w-5 fill-amber-400 text-amber-400" />
        {Number(rating).toFixed(1)} · {reviewCount} avis
      </h2>
      <ul className="grid gap-4 sm:grid-cols-2">
        {reviews.map((review) => (
          <li key={review.public_id} className="rounded-xl border bg-card p-4">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{review.author_name}</span>
              <Stars rating={review.rating} />
            </div>
            {review.comment && (
              <p className="mt-2 text-sm leading-relaxed text-foreground/90">{review.comment}</p>
            )}
            <p className="mt-2 text-xs text-muted-foreground">{formatDate(review.created_at)}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
