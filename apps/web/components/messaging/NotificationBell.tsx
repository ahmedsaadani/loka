"use client";

import { Bell } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/api/auth-context";

/** Cloche de messagerie : pastille du nombre de messages non lus, rafraîchie périodiquement. */
export function NotificationBell() {
  const { status } = useAuth();
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (status !== "authenticated") {
      setCount(0);
      return;
    }
    let active = true;
    const load = () =>
      api
        .get<{ count: number }>("/messaging/unread/")
        .then((d) => active && setCount(d.count))
        .catch(() => undefined);
    load();
    const id = setInterval(load, 45000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [status]);

  if (status !== "authenticated") return null;

  return (
    <Button variant="ghost" size="icon" asChild aria-label="Messages" className="relative">
      <Link href="/messages">
        <Bell className="h-5 w-5" />
        {count > 0 && (
          <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </Link>
    </Button>
  );
}
