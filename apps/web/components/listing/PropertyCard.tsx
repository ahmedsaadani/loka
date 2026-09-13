import { BedDouble, Ruler, Users } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { ConditionBadge } from "@/components/listing/ConditionBadge";
import { PriceTag } from "@/components/listing/PriceTag";
import { VerifiedBadge } from "@/components/listing/VerifiedBadge";
import type { PropertyCard as PropertyCardData } from "@/lib/api/types";
import { cn, PROPERTY_TYPE_LABEL } from "@/lib/utils";

interface Props {
  property: PropertyCardData;
  preferredMode?: string;
  priority?: boolean;
  className?: string;
  onHover?: (publicId: string | null) => void;
  highlighted?: boolean;
}

export function PropertyCard({
  property,
  preferredMode,
  priority = false,
  className,
  onHover,
  highlighted,
}: Props) {
  const cover = property.cover_photo?.variants.card;
  const nearest = Object.entries(property.distance_notes)[0];
  const typeLabel =
    property.rooms_label || PROPERTY_TYPE_LABEL[property.property_type] || property.property_type;

  return (
    <article
      className={cn(
        "group overflow-hidden rounded-xl border bg-card shadow-card transition-shadow hover:shadow-float",
        highlighted && "ring-2 ring-primary",
        className,
      )}
      onMouseEnter={onHover ? () => onHover(property.public_id) : undefined}
      onMouseLeave={onHover ? () => onHover(null) : undefined}
      data-testid="property-card"
    >
      <Link href={`/logement/${property.slug}`} className="block focus-visible:outline-none">
        <div className="relative aspect-[4/3] w-full overflow-hidden bg-muted">
          {cover ? (
            <Image
              src={cover}
              alt={property.cover_photo?.alt_text || property.title}
              fill
              sizes="(min-width: 1280px) 25vw, (min-width: 768px) 33vw, 100vw"
              className="object-cover transition-transform duration-300 group-hover:scale-[1.03]"
              priority={priority}
            />
          ) : (
            <div className="grid h-full w-full place-items-center text-sm text-muted-foreground">
              Photos en préparation
            </div>
          )}
          <div className="absolute left-3 top-3 flex flex-wrap gap-1.5">
            <VerifiedBadge level={property.verification_level} />
          </div>
        </div>
        <div className="space-y-2 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {typeLabel} · {property.neighborhood?.name ?? property.city.name}
                {property.neighborhood ? `, ${property.city.name}` : ""}
              </p>
              <h3 className="mt-0.5 line-clamp-2 text-base font-semibold leading-snug group-hover:text-primary">
                {property.title}
              </h3>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {property.bedrooms > 0 && (
              <span className="inline-flex items-center gap-1">
                <BedDouble className="h-3.5 w-3.5" /> {property.bedrooms} ch.
              </span>
            )}
            {property.surface_m2 && (
              <span className="inline-flex items-center gap-1">
                <Ruler className="h-3.5 w-3.5" /> {property.surface_m2} m²
              </span>
            )}
            <span className="inline-flex items-center gap-1">
              <Users className="h-3.5 w-3.5" /> {property.max_guests}
            </span>
            {nearest && (
              <span className="truncate">
                · {nearest[0]} {nearest[1]}
              </span>
            )}
          </div>
          <div className="flex items-end justify-between gap-2 pt-1">
            <PriceTag plans={property.pricing_plans} preferredMode={preferredMode} />
            <ConditionBadge grade={property.condition_grade} />
          </div>
        </div>
      </Link>
    </article>
  );
}
