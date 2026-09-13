"use client";

import { BookingList } from "@/components/booking/BookingList";
import { useApi } from "@/lib/api/hooks";
import type { Booking, Paginated } from "@/lib/api/types";

export default function MyBookingsPage() {
  const { data, loading, refetch } = useApi<Paginated<Booking>>("/bookings/bookings/", {
    page_size: 50,
  });
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl md:text-3xl">Mes réservations</h1>
        <p className="text-muted-foreground">
          L&apos;adresse exacte et le contact de l&apos;hôte apparaissent dans le détail dès la
          confirmation.
        </p>
      </div>
      <BookingList
        bookings={data?.results ?? null}
        loading={loading}
        perspective="traveler"
        onChange={refetch}
      />
    </div>
  );
}
