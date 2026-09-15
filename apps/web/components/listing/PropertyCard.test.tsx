import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { PropertyCard as PropertyCardData } from "@/lib/api/types";

import { PropertyCard } from "./PropertyCard";
import { pickPlan } from "./PriceTag";

const base: PropertyCardData = {
  public_id: "11111111-1111-1111-1111-111111111111",
  slug: "studio-ghazela",
  title: "Studio lumineux à Ghazela",
  property_type: "studio",
  rooms_label: "",
  bedrooms: 0,
  bathrooms: 1,
  surface_m2: 30,
  furnished: true,
  max_guests: 1,
  city: { name: "Ariana", slug: "ariana" },
  neighborhood: { name: "Ghazela", slug: "ghazela" },
  location: { lat: 36.897, lng: 10.187 },
  location_precision: "approximate",
  cover_photo: {
    public_id: "22222222-2222-2222-2222-222222222222",
    variants: { card: "http://localhost:9000/loka-public/photos/1/card.webp" },
    width: 640,
    height: 480,
    alt_text: "Séjour",
    is_cover: true,
    taken_by_team: true,
    order: 1,
  },
  pricing_plans: [
    {
      rental_mode: "nightly",
      price: "120.00",
      price_eur: "35.40",
      monthly_equivalent: null,
      min_duration: 2,
      max_duration: 30,
      is_active: true,
    },
    {
      rental_mode: "monthly",
      price: "850.00",
      price_eur: "250.75",
      monthly_equivalent: null,
      min_duration: 1,
      max_duration: 11,
      is_active: true,
    },
  ],
  verification_level: "verified",
  condition_grade: "excellent",
  verified_at: "2026-08-01T10:00:00Z",
  distance_notes: { ESPRIT: "8 min à pied" },
  rating: "4.8",
  review_count: 23,
};

describe("PropertyCard", () => {
  it("renders title, verified badge, monthly price by default and link", () => {
    render(<PropertyCard property={base} />);
    expect(screen.getByRole("heading", { name: /Studio lumineux/ })).toBeInTheDocument();
    expect(screen.getByText("Vérifié par Loka")).toBeInTheDocument();
    expect(screen.getByText(/850\s?DT/)).toBeInTheDocument();
    expect(screen.getByText("Excellent état")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute("href", "/logement/studio-ghazela");
    expect(screen.getByText(/ESPRIT 8 min à pied/)).toBeInTheDocument();
  });

  it("uses the preferred rental mode when available", () => {
    render(<PropertyCard property={base} preferredMode="nightly" />);
    expect(screen.getByText(/120\s?DT/)).toBeInTheDocument();
  });

  it("shows placeholder without cover photo and selection badge", () => {
    render(
      <PropertyCard property={{ ...base, cover_photo: null, verification_level: "selection" }} />,
    );
    expect(screen.getByText("Photos en préparation")).toBeInTheDocument();
    expect(screen.getByText("Sélection Loka")).toBeInTheDocument();
  });
});

describe("pickPlan", () => {
  it("falls back to monthly then nightly then yearly", () => {
    expect(pickPlan(base.pricing_plans)?.rental_mode).toBe("monthly");
    expect(pickPlan(base.pricing_plans, "yearly")?.rental_mode).toBe("monthly");
    expect(pickPlan([{ ...base.pricing_plans[0]!, is_active: false }])).toBeUndefined();
  });
});
