"use client";

import { MessageSquare } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/api/auth-context";
import type { Conversation, Paginated } from "@/lib/api/types";
import { formatDate } from "@/lib/utils";

export default function MessagesPage() {
  const { status } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<Conversation[] | null>(null);

  useEffect(() => {
    if (status === "anonymous") {
      router.replace("/connexion?next=/messages");
      return;
    }
    if (status !== "authenticated") return;
    let active = true;
    api
      .get<Paginated<Conversation>>("/messaging/conversations/")
      .then((d) => active && setItems(d.results))
      .catch(() => active && setItems([]));
    return () => {
      active = false;
    };
  }, [status, router]);

  return (
    <div className="container max-w-3xl py-8 md:py-12">
      <h1 className="mb-6 text-2xl md:text-3xl">Messages</h1>
      {items === null ? (
        <p className="text-muted-foreground">Chargement…</p>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border bg-card p-10 text-center">
          <MessageSquare className="mx-auto h-10 w-10 text-muted-foreground" />
          <p className="mt-4 text-lg font-medium">Aucune conversation</p>
          <p className="mt-1 text-muted-foreground">
            Contactez un hôte depuis la fiche d&apos;un logement pour démarrer une discussion.
          </p>
          <Button asChild className="mt-6">
            <Link href="/recherche">Parcourir les logements</Link>
          </Button>
        </div>
      ) : (
        <ul className="divide-y rounded-2xl border bg-card">
          {items.map((c) => (
            <li key={c.public_id}>
              <Link
                href={`/messages/${c.public_id}`}
                className="flex items-center gap-4 p-4 transition-colors hover:bg-accent/50"
              >
                <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-muted">
                  {c.property.cover && (
                    <Image
                      src={c.property.cover}
                      alt={c.property.title}
                      fill
                      sizes="56px"
                      className="object-cover"
                    />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate font-medium">
                      {c.other_party.name}
                      <span className="ml-2 text-xs font-normal text-muted-foreground">
                        {c.other_party.role}
                      </span>
                    </p>
                    {c.unread_count > 0 && (
                      <span className="grid h-5 min-w-5 place-items-center rounded-full bg-primary px-1.5 text-xs font-semibold text-primary-foreground">
                        {c.unread_count}
                      </span>
                    )}
                  </div>
                  <p className="truncate text-sm text-muted-foreground">{c.property.title}</p>
                  {c.last_message && (
                    <p className="truncate text-sm text-muted-foreground">
                      {c.last_message.is_me ? "Vous : " : ""}
                      {c.last_message.body}
                    </p>
                  )}
                </div>
                {c.last_message_at && (
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {formatDate(c.last_message_at)}
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
