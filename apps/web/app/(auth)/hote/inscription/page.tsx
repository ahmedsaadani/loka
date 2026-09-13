import { RegisterForm } from "@/components/auth/RegisterForm";
import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata({
  title: "Proposer un bien : créer un compte propriétaire",
  description:
    "Créez votre compte propriétaire Loka : nous visitons, photographions et publions votre bien.",
  path: "/hote/inscription",
});

type SearchParams = Promise<{ next?: string }>;

export default async function HostRegisterPage({ searchParams }: { searchParams: SearchParams }) {
  const { next } = await searchParams;
  return <RegisterForm role="host" next={next ?? null} />;
}
