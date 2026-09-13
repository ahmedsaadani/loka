import { expect, test } from "@playwright/test";

import { ACCOUNTS, API_URL, apiToken, gotoReady, isoDate, login } from "./helpers";

test.describe("Parcours voyageur : recherche → fiche → demande de réservation", () => {
  test("recherche, ouverture d'une fiche et envoi d'une demande", async ({ page, request }) => {
    // Nettoyage : retire les demandes en attente laissées par un run précédent.
    const token = await apiToken(request, ACCOUNTS.traveler);
    const pending = await request.get(`${API_URL}/bookings/requests/?status=pending&page_size=50`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const list = (await pending.json()) as {
      results: Array<{ public_id: string; status: string }>;
    };
    for (const r of list.results.filter((x) => x.status === "pending")) {
      await request.post(`${API_URL}/bookings/requests/${r.public_id}/cancel/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    }

    await gotoReady(page, "/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "Louez un logement vérifié",
    );

    // Recherche à la nuit à Ariana
    await page.getByTestId("mode-nightly").click();
    await page.getByTestId("search-city").click();
    await page.getByRole("option", { name: "Ariana" }).click();
    await expect(page.getByRole("listbox")).toBeHidden();
    // Entrée dans le champ voyageurs : évite le clic pendant la fermeture du menu déroulant.
    await page.getByLabel("Voyageurs").press("Enter");
    await expect(page).toHaveURL(/\/recherche\?.*city=ariana/);
    await expect(page).toHaveURL(/rental_mode=nightly/);

    const cards = page.getByTestId("property-card");
    await expect(cards.first()).toBeVisible();
    const firstTitle = await cards.first().getByRole("heading").innerText();
    await cards.first().getByRole("link").first().click();

    // Fiche bien
    await expect(page).toHaveURL(/\/logement\//);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(firstTitle.slice(0, 20));
    await expect(page.getByText("Vérifié par Loka").first()).toBeVisible();
    const listingUrl = page.url();

    // Sur mobile, le bloc de réservation est replié dans un <details> sticky.
    const openBookingBox = async () => {
      const opener = page.getByTestId("mobile-booking-open");
      if (await opener.isVisible()) {
        if ((await opener.getAttribute("aria-expanded")) !== "true") await opener.click();
      }
    };
    const visibleBox = () => page.getByTestId("booking-box").locator("visible=true").first();

    // Non connecté : le bloc réservation renvoie vers la connexion
    await openBookingBox();
    const loginLink = visibleBox().getByRole("link", {
      name: /Connectez-vous pour envoyer une demande/,
    });
    await expect(loginLink).toBeVisible();
    await login(page, ACCOUNTS.traveler, new URL(listingUrl).pathname);
    await expect(page).toHaveURL(listingUrl);

    // Demande de réservation (nuitée, dates lointaines pour éviter les blocs)
    await openBookingBox();
    const box = visibleBox();
    await box.getByTestId("booking-mode-nightly").click();
    await box.getByTestId("booking-start").fill(isoDate(120));
    await box.getByTestId("booking-end").fill(isoDate(124));
    await expect(box.getByTestId("quote")).toBeVisible({ timeout: 15_000 });
    await expect(box.getByTestId("quote")).toContainText("Frais de service");
    await box.getByTestId("booking-submit").click();

    await expect(page).toHaveURL(/\/compte\/demandes/, { timeout: 60_000 });
    const row = page.getByTestId("request-row").first();
    await expect(row).toBeVisible();
    await expect(row).toContainText("En attente");
  });
});
