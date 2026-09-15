"use client";

import { Check, Coins } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CURRENCIES, useCurrency } from "@/lib/currency";

const LABELS: Record<string, string> = {
  TND: "Dinar (DT)",
  EUR: "Euro (€)",
  USD: "Dollar ($)",
};

export function CurrencySwitcher() {
  const { currency, setCurrency } = useCurrency();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1.5" aria-label="Changer de devise">
          <Coins className="h-4 w-4" />
          <span className="font-medium">{currency}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {CURRENCIES.map((c) => (
          <DropdownMenuItem
            key={c}
            onClick={() => setCurrency(c)}
            className="justify-between gap-6"
          >
            {LABELS[c]}
            {currency === c && <Check className="h-4 w-4 text-primary" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
