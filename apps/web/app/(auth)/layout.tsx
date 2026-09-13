import { Logo } from "@/components/layout/Logo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="container flex h-16 items-center">
        <Logo />
      </header>
      <main className="container flex flex-1 items-start justify-center py-8 md:items-center">
        <div className="w-full max-w-md rounded-2xl border bg-card p-6 shadow-card md:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
