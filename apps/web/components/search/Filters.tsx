"use client";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Amenity, CitySummary, NeighborhoodSummary } from "@/lib/api/types";
import { t } from "@/lib/i18n";
import { PROPERTY_TYPE_LABEL } from "@/lib/utils";

export interface FilterValues {
  city: string;
  neighborhood: string;
  rental_mode: string;
  min_price: string;
  max_price: string;
  property_type: string[];
  bedrooms_min: string;
  guests: string;
  furnished: boolean;
  amenities: string[];
  start: string;
  end: string;
  ordering: string;
}

export const EMPTY_FILTERS: FilterValues = {
  city: "",
  neighborhood: "",
  rental_mode: "monthly",
  min_price: "",
  max_price: "",
  property_type: [],
  bedrooms_min: "",
  guests: "",
  furnished: false,
  amenities: [],
  start: "",
  end: "",
  ordering: "newest",
};

interface Props {
  values: FilterValues;
  onChange: (next: FilterValues) => void;
  onReset: () => void;
  cities: CitySummary[];
  neighborhoods: NeighborhoodSummary[];
  amenities: Amenity[];
}

export function Filters({ values, onChange, onReset, cities, neighborhoods, amenities }: Props) {
  const set = <K extends keyof FilterValues>(key: K, value: FilterValues[K]) =>
    onChange({ ...values, [key]: value });
  const toggle = (key: "property_type" | "amenities", item: string) => {
    const list = values[key];
    set(key, list.includes(item) ? list.filter((v) => v !== item) : [...list, item]);
  };

  return (
    <div className="space-y-5" data-testid="filters">
      <div className="space-y-1">
        <Label htmlFor="f-city">{t.search.where}</Label>
        <Select
          value={values.city || "all"}
          onValueChange={(v) =>
            onChange({ ...values, city: v === "all" ? "" : v, neighborhood: "" })
          }
        >
          <SelectTrigger id="f-city">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Toute la Tunisie</SelectItem>
            {cities.map((c) => (
              <SelectItem key={c.slug} value={c.slug}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {neighborhoods.length > 0 && (
        <div className="space-y-1">
          <Label htmlFor="f-neighborhood">{t.search.neighborhood}</Label>
          <Select
            value={values.neighborhood || "all"}
            onValueChange={(v) => set("neighborhood", v === "all" ? "" : v)}
          >
            <SelectTrigger id="f-neighborhood">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les quartiers</SelectItem>
              {neighborhoods.map((n) => (
                <SelectItem key={n.slug} value={n.slug}>
                  {n.name} ({n.property_count})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">{t.search.price} (DT)</legend>
        <div className="grid grid-cols-2 gap-2">
          <Input
            type="number"
            inputMode="numeric"
            min={0}
            placeholder={t.search.minPrice}
            aria-label={t.search.minPrice}
            value={values.min_price}
            onChange={(e) => set("min_price", e.target.value)}
          />
          <Input
            type="number"
            inputMode="numeric"
            min={0}
            placeholder={t.search.maxPrice}
            aria-label={t.search.maxPrice}
            value={values.max_price}
            onChange={(e) => set("max_price", e.target.value)}
          />
        </div>
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">{t.search.type}</legend>
        {Object.entries(PROPERTY_TYPE_LABEL).map(([value, label]) => (
          <label key={value} className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={values.property_type.includes(value)}
              onCheckedChange={() => toggle("property_type", value)}
            />
            {label}
          </label>
        ))}
      </fieldset>

      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <Label htmlFor="f-bedrooms">{t.search.bedrooms} min.</Label>
          <Input
            id="f-bedrooms"
            type="number"
            inputMode="numeric"
            min={0}
            max={10}
            value={values.bedrooms_min}
            onChange={(e) => set("bedrooms_min", e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="f-guests">{t.search.guests}</Label>
          <Input
            id="f-guests"
            type="number"
            inputMode="numeric"
            min={1}
            max={20}
            value={values.guests}
            onChange={(e) => set("guests", e.target.value)}
          />
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <Checkbox
          checked={values.furnished}
          onCheckedChange={(c) => set("furnished", c === true)}
        />
        {t.search.furnished}
      </label>

      {amenities.length > 0 && (
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">{t.search.amenities}</legend>
          <div className="grid grid-cols-2 gap-1">
            {amenities.map((a) => (
              <label key={a.code} className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={values.amenities.includes(a.code)}
                  onCheckedChange={() => toggle("amenities", a.code)}
                />
                {a.name}
              </label>
            ))}
          </div>
        </fieldset>
      )}

      <Button variant="ghost" className="w-full" onClick={onReset}>
        {t.search.reset}
      </Button>
    </div>
  );
}
