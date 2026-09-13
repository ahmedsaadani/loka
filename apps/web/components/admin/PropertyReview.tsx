"use client";

import Link from "next/link";

import { PropertyActions } from "@/components/admin/PropertyActions";
import { ErrorNote } from "@/components/admin/shared";
import { StatusBadge } from "@/components/admin/StatusBadge";
import { TeamPhotos } from "@/components/admin/TeamPhotos";
import { ConditionBadge } from "@/components/listing/ConditionBadge";
import { VerifiedBadge } from "@/components/listing/VerifiedBadge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/lib/api/hooks";
import type { PropertyStaff } from "@/lib/api/types";
import { PROPERTY_TYPE_LABEL, RENTAL_MODE_TITLE, formatDate, formatTnd } from "@/lib/utils";

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium">{value ?? "—"}</dd>
    </div>
  );
}

function yesNo(value: boolean): string {
  return value ? "Oui" : "Non";
}

export function PropertyReview({ id }: { id: string }) {
  const { data, error, loading, refetch } = useApi<PropertyStaff>(
    `/listings/staff/properties/${id}/`,
  );

  if (loading && !data) {
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="space-y-4">
        <ErrorNote error={error} />
        <Link href="/admin/validation" className="text-sm underline">
          Retour à la file de validation
        </Link>
      </div>
    );
  }

  const p = data;
  const readiness = Object.entries(p.readiness_errors ?? {});
  const distances = Object.entries(p.distance_notes ?? {});

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Link href="/admin/validation" className="text-xs text-muted-foreground hover:underline">
          ← File de validation
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-semibold">{p.title || "Sans titre"}</h1>
          <StatusBadge kind="property" status={p.status} />
          {p.status === "published" && (
            <VerifiedBadge level={p.verification_level} verifiedAt={p.verified_at} showDate />
          )}
          <ConditionBadge grade={p.condition_grade} />
        </div>
        <p className="text-sm text-muted-foreground">
          {PROPERTY_TYPE_LABEL[p.property_type] ?? p.property_type} · {p.city.name}
          {p.neighborhood ? ` · ${p.neighborhood.name}` : ""} · créé le {formatDate(p.created_at)}
          {p.published_at ? ` · publié le ${formatDate(p.published_at)}` : ""}
        </p>
        {p.visit_scheduled_at && (
          <p className="text-sm">
            Visite planifiée le{" "}
            {formatDate(p.visit_scheduled_at, {
              day: "numeric",
              month: "long",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        )}
        {p.rejection_reason && (
          <p className="text-sm text-destructive">Motif du dernier rejet : {p.rejection_reason}</p>
        )}
      </div>

      {readiness.length > 0 && (
        <div
          role="alert"
          className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm"
          data-testid="readiness-errors"
        >
          <p className="font-medium">Prérequis manquants pour la publication</p>
          <ul className="mt-1 list-inside list-disc">
            {readiness.map(([key, msg]) => (
              <li key={key}>{msg}</li>
            ))}
          </ul>
        </div>
      )}

      <PropertyActions property={p} onDone={refetch} />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Informations</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-3">
              <Field label="Type" value={PROPERTY_TYPE_LABEL[p.property_type] ?? p.property_type} />
              <Field label="Pièces" value={p.rooms_label} />
              <Field label="Chambres / SdB" value={`${p.bedrooms} / ${p.bathrooms}`} />
              <Field label="Surface" value={p.surface_m2 ? `${p.surface_m2} m²` : "—"} />
              <Field label="Voyageurs max" value={p.max_guests} />
              <Field label="Meublé" value={yesNo(p.furnished)} />
              <Field
                label="Étage / ascenseur"
                value={`${p.floor ?? "—"} / ${yesNo(p.has_elevator)}`}
              />
              <Field label="Charges incluses" value={yesNo(p.charges_included)} />
              <Field
                label="Charges mensuelles estimées"
                value={p.monthly_charges_estimate ? formatTnd(p.monthly_charges_estimate) : "—"}
              />
              <Field label="Caution (mois)" value={p.deposit_months} />
              <Field label="Bail minimum (mois)" value={p.min_lease_months} />
            </dl>
            {distances.length > 0 && (
              <div className="mt-4">
                <p className="text-xs text-muted-foreground">Distances</p>
                <ul className="text-sm">
                  {distances.map(([k, v]) => (
                    <li key={k}>
                      {k} : {v}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {p.description && (
              <div className="mt-4">
                <p className="text-xs text-muted-foreground">Description</p>
                <p className="whitespace-pre-line text-sm">{p.description}</p>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                Adresse exacte
                <Badge variant="destructive">Interne — accès journalisé</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm font-medium" data-testid="address-private">
                {p.address_private || "Non renseignée"}
              </p>
              {p.location && (
                <p className="text-xs text-muted-foreground">
                  {p.location.lat.toFixed(5)}, {p.location.lng.toFixed(5)} · précision{" "}
                  {p.location_precision === "exact" ? "exacte" : "approximative"}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Hôte</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-medium">{p.host_email}</span>
              {p.host_identity_verified ? (
                <Badge variant="verified">Identité vérifiée</Badge>
              ) : (
                <Badge variant="muted">Identité non vérifiée</Badge>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Tarifs</CardTitle>
            </CardHeader>
            <CardContent>
              {p.pricing_plans.length === 0 ? (
                <p className="text-sm text-muted-foreground">Aucun tarif défini.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-xs text-muted-foreground">
                      <tr>
                        <th className="py-1 pr-2">Mode</th>
                        <th className="py-1 pr-2">Prix</th>
                        <th className="py-1 pr-2">Durée min / max</th>
                        <th className="py-1">Actif</th>
                      </tr>
                    </thead>
                    <tbody>
                      {p.pricing_plans.map((plan) => (
                        <tr key={plan.rental_mode} className="border-t">
                          <td className="py-1 pr-2">
                            {RENTAL_MODE_TITLE[plan.rental_mode] ?? plan.rental_mode}
                          </td>
                          <td className="py-1 pr-2">{formatTnd(plan.price)}</td>
                          <td className="py-1 pr-2">
                            {plan.min_duration} / {plan.max_duration ?? "—"}
                          </td>
                          <td className="py-1">{yesNo(plan.is_active)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <TeamPhotos propertyId={p.public_id} photos={p.photos} onChanged={refetch} />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Notes de vérification</CardTitle>
        </CardHeader>
        <CardContent>
          <textarea
            readOnly
            value={p.verification_notes || ""}
            placeholder="Aucune note."
            rows={4}
            className="w-full rounded-md border bg-muted/40 p-2 text-sm"
          />
        </CardContent>
      </Card>
    </div>
  );
}
