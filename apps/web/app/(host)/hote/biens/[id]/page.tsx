"use client";

import { useParams } from "next/navigation";

import { PropertyWizard } from "@/components/host/PropertyWizard";

export default function EditPropertyPage() {
  const { id } = useParams<{ id: string }>();
  return <PropertyWizard publicId={id} />;
}
