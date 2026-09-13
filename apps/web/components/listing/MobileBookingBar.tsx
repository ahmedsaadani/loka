"use client";

import { useState } from "react";

import { BookingBox } from "@/components/listing/BookingBox";
import { pickPlan } from "@/components/listing/PriceTag";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import type { PricingPlan } from "@/lib/api/types";
import { t } from "@/lib/i18n";
import { formatTnd, RENTAL_MODE_LABEL } from "@/lib/utils";

interface Props {
  slug: string;
  plans: PricingPlan[];
  maxGuests: number;
}

/** Barre sticky mobile : prix + bouton qui ouvre le bloc de réservation dans un panneau bas. */
export function MobileBookingBar({ slug, plans, maxGuests }: Props) {
  const [open, setOpen] = useState(false);
  const plan = pickPlan(plans);
  return (
    <>
      <div className="safe-bottom fixed inset-x-0 bottom-0 z-30 flex items-center justify-between gap-3 border-t bg-background/95 p-3 backdrop-blur lg:hidden">
        <span className="text-lg font-semibold">
          {plan ? formatTnd(plan.price) : ""}
          {plan && (
            <span className="text-sm font-normal text-muted-foreground">
              {" "}
              / {RENTAL_MODE_LABEL[plan.rental_mode]}
            </span>
          )}
        </span>
        <Button
          onClick={() => setOpen(true)}
          data-testid="mobile-booking-open"
          aria-expanded={open}
        >
          {t.listing.book}
        </Button>
      </div>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="bottom" className="max-h-[92vh] overflow-y-auto p-4">
          <SheetTitle className="sr-only">{t.listing.book}</SheetTitle>
          <BookingBox
            slug={slug}
            plans={plans}
            maxGuests={maxGuests}
            className="border-0 p-0 shadow-none"
          />
        </SheetContent>
      </Sheet>
    </>
  );
}
