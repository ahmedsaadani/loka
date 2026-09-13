import { PropertyReview } from "@/components/admin/PropertyReview";

export default async function AdminPropertyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <PropertyReview id={id} />;
}
