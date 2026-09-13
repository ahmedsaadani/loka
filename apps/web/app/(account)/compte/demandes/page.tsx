"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { RequestList } from "@/components/booking/RequestList";
import { useApi } from "@/lib/api/hooks";
import type { BookingRequest, Paginated } from "@/lib/api/types";

function MyRequests() {
  const focus = useSearchParams().get("focus");
  const { data, loading, refetch } = useApi<Paginated<BookingRequest>>("/bookings/requests/", {
    page_size: 50,
  });
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl md:text-3xl">Mes demandes</h1>
        <p className="text-muted-foreground">
          L&apos;hôte dispose de 48 h pour répondre. Une fois acceptée, payez l&apos;acompte pour
          confirmer.
        </p>
      </div>
      <RequestList
        requests={data?.results ?? null}
        loading={loading}
        perspective="traveler"
        onChange={refetch}
        focus={focus}
      />
    </div>
  );
}

export default function MyRequestsPage() {
  return (
    <Suspense>
      <MyRequests />
    </Suspense>
  );
}
