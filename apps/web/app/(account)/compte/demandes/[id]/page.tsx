import { redirect } from "next/navigation";

/** Les liens des emails pointent ici ; la liste met la demande en évidence. */
export default async function RequestDetailRedirect({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/compte/demandes?focus=${encodeURIComponent(id)}`);
}
