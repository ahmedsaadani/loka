"use client";

import { ArrowLeft, Send } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiRequestError } from "@/lib/api/client";
import { useAuth } from "@/lib/api/auth-context";
import type { ConversationDetail, Message } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export default function ThreadPage() {
  const { status } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [conv, setConv] = useState<ConversationDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (status === "anonymous") {
      router.replace(`/connexion?next=/messages/${params.id}`);
      return;
    }
    if (status !== "authenticated") return;
    let active = true;
    api
      .get<ConversationDetail>(`/messaging/conversations/${params.id}/`)
      .then((d) => {
        if (!active) return;
        setConv(d);
        setMessages(d.messages);
      })
      .catch(() => active && router.replace("/messages"));
    return () => {
      active = false;
    };
  }, [status, params.id, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const text = body.trim();
    if (!text || sending) return;
    setSending(true);
    try {
      const msg = await api.post<Message>(`/messaging/conversations/${params.id}/messages/`, {
        body: text,
      });
      setMessages((m) => [...m, msg]);
      setBody("");
    } catch (error) {
      if (error instanceof ApiRequestError) alert(error.message);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="container flex max-w-3xl flex-col py-6" style={{ minHeight: "70vh" }}>
      <div className="mb-4 flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild aria-label="Retour">
          <Link href="/messages">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
        {conv && (
          <div className="min-w-0">
            <p className="truncate font-semibold">{conv.other_party.name}</p>
            <Link
              href={`/logement/${conv.property.slug}`}
              className="truncate text-sm text-muted-foreground hover:text-foreground"
            >
              {conv.property.title}
            </Link>
          </div>
        )}
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto rounded-2xl border bg-card p-4">
        {messages.length === 0 ? (
          <p className="py-8 text-center text-muted-foreground">Aucun message.</p>
        ) : (
          messages.map((m) => (
            <div
              key={m.public_id}
              className={cn("flex", m.is_me ? "justify-end" : "justify-start")}
            >
              <div
                className={cn(
                  "max-w-[80%] whitespace-pre-line rounded-2xl px-4 py-2 text-sm",
                  m.is_me
                    ? "rounded-br-sm bg-primary text-primary-foreground"
                    : "rounded-bl-sm bg-muted",
                )}
              >
                {m.body}
              </div>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={send} className="mt-3 flex items-end gap-2">
        <Textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Écrire un message…"
          rows={2}
          maxLength={4000}
          className="resize-none"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send(e);
            }
          }}
        />
        <Button type="submit" size="icon" disabled={sending || !body.trim()} aria-label="Envoyer">
          <Send className="h-5 w-5" />
        </Button>
      </form>
    </div>
  );
}
