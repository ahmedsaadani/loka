import { RegisterForm } from "@/components/auth/RegisterForm";
import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata({
  title: "Inscription",
  description: "Créez votre compte voyageur Loka.",
  path: "/inscription",
  noindex: true,
});

type SearchParams = Promise<{ next?: string }>;

export default async function RegisterPage({ searchParams }: { searchParams: SearchParams }) {
  const { next } = await searchParams;
  return <RegisterForm role="traveler" next={next ?? null} />;
}
