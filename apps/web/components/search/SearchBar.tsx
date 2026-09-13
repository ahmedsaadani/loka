"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { CitySummary, RentalMode } from "@/lib/api/types";
import { t } from "@/lib/i18n";
import { cn, RENTAL_MODE_TITLE } from "@/lib/utils";

interface Props {
  cities: CitySummary[];
  compact?: boolean;
  initial?: Partial<SearchValues>;
  className?: string;
}

export interface SearchValues {
  city: string;
  rental_mode: RentalMode;
  guests: string;
  start: string;
  end: string;
}

const MODES: RentalMode[] = ["nightly", "monthly", "yearly"];

export function SearchBar({ cities, compact = false, initial, className }: Props) {
  const router = useRouter();
  const [values, setValues] = useState<SearchValues>({
    city: initial?.city ?? "",
    rental_mode: initial?.rental_mode ?? "monthly",
    guests: initial?.guests ?? "1",
    start: initial?.start ?? "",
    end: initial?.end ?? "",
  });

  function update<K extends keyof SearchValues>(key: K, value: SearchValues[K]) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams();
    if (values.city) params.set("city", values.city);
    params.set("rental_mode", values.rental_mode);
    if (values.guests && values.guests !== "1") params.set("guests", values.guests);
    if (values.start && values.end) {
      params.set("start", values.start);
      params.set("end", values.end);
    }
    router.push(`/recherche?${params.toString()}`);
  }

  return (
    <form
      onSubmit={submit}
      className={cn("rounded-2xl border bg-card p-3 shadow-float md:p-4", className)}
      role="search"
      aria-label="Rechercher un logement"
    >
      <Tabs
        value={values.rental_mode}
        onValueChange={(v) => update("rental_mode", v as RentalMode)}
        className="mb-3"
      >
        <TabsList className="grid w-full grid-cols-3 md:inline-flex md:w-auto">
          {MODES.map((mode) => (
            <TabsTrigger key={mode} value={mode} data-testid={`mode-${mode}`}>
              {RENTAL_MODE_TITLE[mode]}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div
        className={cn(
          "grid gap-3",
          compact ? "md:grid-cols-[1fr_auto_auto]" : "md:grid-cols-[1.4fr_1fr_1fr_0.8fr_auto]",
        )}
      >
        <div className="space-y-1">
          <Label htmlFor="search-city">{t.search.where}</Label>
          <Select
            value={values.city || "all"}
            onValueChange={(v) => update("city", v === "all" ? "" : v)}
          >
            <SelectTrigger id="search-city" data-testid="search-city">
              <SelectValue placeholder={t.search.wherePlaceholder} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Toute la Tunisie</SelectItem>
              {cities.map((city) => (
                <SelectItem key={city.slug} value={city.slug}>
                  {city.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {!compact && (
          <>
            <div className="space-y-1">
              <Label htmlFor="search-start">{t.search.from}</Label>
              <Input
                id="search-start"
                type="date"
                value={values.start}
                onChange={(e) => update("start", e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="search-end">{t.search.to}</Label>
              <Input
                id="search-end"
                type="date"
                value={values.end}
                min={values.start}
                onChange={(e) => update("end", e.target.value)}
              />
            </div>
          </>
        )}

        <div className="space-y-1">
          <Label htmlFor="search-guests">{t.search.guests}</Label>
          <Input
            id="search-guests"
            type="number"
            min={1}
            max={20}
            inputMode="numeric"
            value={values.guests}
            onChange={(e) => update("guests", e.target.value)}
          />
        </div>

        <div className="flex items-end">
          <Button type="submit" size="lg" className="w-full md:w-auto" data-testid="search-submit">
            <Search /> {t.search.submit}
          </Button>
        </div>
      </div>
    </form>
  );
}
