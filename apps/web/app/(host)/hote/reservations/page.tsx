"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { BookingList } from "@/components/booking/BookingList";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/lib/api/hooks";
import type { Booking, Paginated } from "@/lib/api/types";

const TABS = [
  { value: "", label: "Toutes" },
  { value: "awaiting_deposit", label: "Acompte en attente" },
  { value: "confirmed", label: "Confirmées" },
  { value: "in_progress", label: "En cours" },
  { value: "completed", label: "Terminées" },
  { value: "cancelled", label: "Annulées" },
];

function HostBookings() {
  const focus = useSearchParams().get("focus");
  const [status, setStatus] = useState("");
  const { data, loading, refetch } = useApi<Paginated<Booking>>("/bookings/host/bookings/", {
    status,
    page_size: 50,
  });
  return (
    <div className="space-y-4">
      <h1 className="text-2xl md:text-3xl">Réservations</h1>
      <Tabs value={status} onValueChange={setStatus}>
        <TabsList className="flex-wrap">
          {TABS.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <BookingList
        bookings={data?.results ?? null}
        loading={loading}
        perspective="host"
        onChange={refetch}
        focus={focus}
      />
    </div>
  );
}

export default function HostBookingsPage() {
  return (
    <Suspense>
      <HostBookings />
    </Suspense>
  );
}
