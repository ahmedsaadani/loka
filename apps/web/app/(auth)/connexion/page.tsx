import { Suspense } from "react";

import { LoginForm } from "@/components/auth/LoginForm";
import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata({
  title: "Connexion",
  description: "Connectez-vous à votre compte Loka.",
  path: "/connexion",
  noindex: true,
});

type SearchParams = Promise<{ next?: string }>;

export default async function LoginPage({ searchParams }: { searchParams: SearchParams }) {
  const { next } = await searchParams;
  return (
    <Suspense>
      <LoginForm next={next ?? null} />
    </Suspense>
  );
}
