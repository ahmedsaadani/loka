/* eslint-disable no-console -- script CLI */
/**
 * Captures d'écran de contrôle visuel (desktop + mobile) des pages publiques,
 * enregistrées dans docs/screenshots/. Nécessite un front lancé (E2E_BASE_URL,
 * défaut http://localhost:3000) alimenté par la base de démo (`manage.py seed`).
 *
 *   node scripts/screenshots.mjs
 */
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium, devices } from "@playwright/test";

const BASE = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const API = process.env.E2E_API_URL ?? "http://localhost:18000/api/v1";
const OUT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../docs/screenshots");

async function firstSlug(query) {
  const res = await fetch(`${API}/listings/properties/?page_size=1&${query}`);
  const data = await res.json();
  return data.results?.[0]?.slug;
}

const apartment = await firstSlug("property_type=apartment&city=ariana&ordering=-published_at");
const villa = await firstSlug("property_type=villa&city=hammamet");
if (!apartment || !villa) throw new Error("Biens de démo introuvables : lancez `manage.py seed`.");

const PAGES = [
  { name: "accueil", url: "/" },
  { name: "ville-ariana", url: "/location/ariana" },
  { name: "fiche-appartement", url: `/logement/${apartment}` },
  { name: "fiche-villa", url: `/logement/${villa}` },
  { name: "recherche-carte", url: "/recherche?city=ariana&rental_mode=monthly", map: true },
];

const VIEWPORTS = {
  desktop: { viewport: { width: 1440, height: 900 } },
  mobile: { ...devices["iPhone 13"], hasTouch: true },
};

await mkdir(OUT, { recursive: true });
const browser = await chromium.launch();
const issues = [];
for (const [device, options] of Object.entries(VIEWPORTS)) {
  const context = await browser.newContext(options);
  const page = await context.newPage();
  for (const spec of PAGES) {
    await page.goto(`${BASE}${spec.url}`, { waitUntil: "networkidle" });
    await page.waitForSelector("html[data-hydrated]", { timeout: 60_000 });
    if (spec.map && device === "mobile") {
      await page.getByTestId("toggle-view").click({ force: true });
    }
    if (spec.map) {
      await page.waitForSelector("canvas", { timeout: 30_000 });
      await page.waitForTimeout(2500);
    }
    // Force le chargement des images paresseuses avant la capture pleine page.
    await page.evaluate(async () => {
      window.scrollTo(0, document.body.scrollHeight);
      await new Promise((r) => setTimeout(r, 600));
      window.scrollTo(0, 0);
      await new Promise((r) => setTimeout(r, 300));
    });
    const fullPage = !(spec.map && device === "mobile");
    const file = path.join(OUT, `${spec.name}-${device}.jpg`);
    await page.screenshot({ path: file, fullPage, type: "jpeg", quality: 80 });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    if (overflow > 0)
      issues.push(`${spec.name} (${device}) : débordement horizontal de ${overflow}px`);
    console.log(`✓ ${path.relative(process.cwd(), file)}`);
  }
  await context.close();
}
await browser.close();
if (issues.length) {
  console.log("\nProblèmes détectés :");
  for (const i of issues) console.log(` - ${i}`);
} else {
  console.log("\nAucun débordement horizontal détecté.");
}
