"use client";

import { Star } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { toast } from "sonner";

import {
  EmptyNote,
  ErrorNote,
  ListSkeleton,
  Pagination,
  errorMessage,
  parsePage,
} from "@/components/admin/shared";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/api/hooks";
import type { Paginated, StaffReview } from "@/lib/api/types";
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

function Reviews() {
  const params = useSearchParams();
  const router = useRouter();
  const published = params.get("published") ?? "";
  const page = parsePage(params.get("page"));
  const { data, loading, error, refetch } = useApi<Paginated<StaffReview>>("/reviews/staff/", {
    published,
    page,
  });

  function setParams(next: Record<string, string>) {
    const sp = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(next)) {
      if (v) sp.set(k, v);
      else sp.delete(k);
    }
    router.replace(`/admin/avis?${sp.toString()}`);
  }

  async function setVisibility(review: StaffReview, isPublished: boolean) {
    try {
      await api.post(`/reviews/staff/${review.public_id}/visibility/`, {
        is_published: isPublished,
      });
      toast.success(isPublished ? "Avis republié." : "Avis masqué.");
      await refetch();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl md:text-3xl">Avis</h1>
        <p className="text-sm text-muted-foreground">
          Modérez les avis des voyageurs. Masquer un avis le retire des fiches et recalcule la note.
        </p>
      </div>

      <Select
        value={published || "all"}
        onValueChange={(v) => setParams({ published: v === "all" ? "" : v, page: "" })}
      >
        <SelectTrigger className="w-[200px]" aria-label="Statut">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Tous les avis</SelectItem>
          <SelectItem value="true">Publiés</SelectItem>
          <SelectItem value="false">Masqués</SelectItem>
        </SelectContent>
      </Select>

      <ErrorNote error={error} />
      {loading && !data ? (
        <ListSkeleton />
      ) : !data || data.results.length === 0 ? (
        <EmptyNote>Aucun avis.</EmptyNote>
      ) : (
        <ul className="divide-y rounded-xl border bg-card">
          {data.results.map((review) => (
            <li key={review.public_id} className="space-y-2 p-4 text-sm">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Stars rating={review.rating} />
                    <span className="font-medium">{review.author_name}</span>
                    {!review.is_published && (
                      <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                        Masqué
                      </span>
                    )}
                  </div>
                  <p className="text-muted-foreground">
                    {review.property_title} · {review.author_email} ·{" "}
                    {formatDate(review.created_at)}
                  </p>
                  {review.comment && (
                    <p className="mt-1 whitespace-pre-line rounded bg-muted p-2 text-xs">
                      {review.comment}
                    </p>
                  )}
                </div>
                {review.is_published ? (
                  <Button size="sm" variant="outline" onClick={() => setVisibility(review, false)}>
                    Masquer
                  </Button>
                ) : (
                  <Button size="sm" onClick={() => setVisibility(review, true)}>
                    Republier
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      {data && (
        <Pagination
          page={page}
          hasPrevious={Boolean(data.previous)}
          hasNext={Boolean(data.next)}
          count={data.count}
          onChange={(p) => setParams({ page: String(p) })}
        />
      )}
    </div>
  );
}

export default function ReviewsPage() {
  return (
    <Suspense fallback={<ListSkeleton />}>
      <Reviews />
    </Suspense>
  );
}
