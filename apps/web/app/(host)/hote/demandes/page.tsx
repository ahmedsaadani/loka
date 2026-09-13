"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { RequestList } from "@/components/booking/RequestList";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/lib/api/hooks";
import type { BookingRequest, Paginated } from "@/lib/api/types";

const TABS = [
  { value: "pending", label: "En attente" },
  { value: "accepted", label: "Acceptées" },
  { value: "declined", label: "Refusées" },
  { value: "", label: "Toutes" },
];

function HostRequests() {
  const focus = useSearchParams().get("focus");
  const [status, setStatus] = useState("pending");
  const { data, loading, refetch } = useApi<Paginated<BookingRequest>>("/bookings/host/requests/", {
    status,
    page_size: 50,
  });
  return (
    <div className="space-y-4">
      <h1 className="text-2xl md:text-3xl">Demandes de réservation</h1>
      <Tabs value={status} onValueChange={setStatus}>
        <TabsList className="flex-wrap">
          {TABS.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <RequestList
        requests={data?.results ?? null}
        loading={loading}
        perspective="host"
        onChange={refetch}
        focus={focus}
      />
    </div>
  );
}

export default function HostRequestsPage() {
  return (
    <Suspense>
      <HostRequests />
    </Suspense>
  );
}
