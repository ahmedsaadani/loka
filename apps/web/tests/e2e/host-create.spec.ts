import { expect, test } from "@playwright/test";

import { ACCOUNTS, gotoReady, login, pngBuffer } from "./helpers";

test.describe("Parcours propriétaire : création d'un bien", () => {
  test("crée un brouillon, complète l'assistant et soumet à validation", async ({ page }) => {
    const title = `Bien Playwright ${Date.now()}`;
    await login(page, ACCOUNTS.host);
    await gotoReady(page, "/hote/biens/nouveau");

    await page.getByTestId("np-title").fill(title);
    await page.getByTestId("np-city").click();
    await page.getByRole("option", { name: "Ariana" }).click();
    // Attend la fermeture du menu déroulant (Radix bloque les clics pendant l'animation).
    await expect(page.getByRole("listbox")).toBeHidden();
    await page.getByTestId("np-submit").click();
    await expect(page).toHaveURL(/\/hote\/biens\/[0-9a-f-]{36}$/, { timeout: 60_000 });
    await expect(page.getByRole("heading", { level: 1 })).toContainText(title);

    // Étape informations
    await page
      .getByTestId("wizard-description")
      .fill(
        "Grand appartement lumineux avec deux chambres, cuisine équipée et balcon, proche des facultés et du métro.",
      );
    await page.getByTestId("wizard-save-infos").click();
    await expect(page.getByText("Enregistré.")).toBeVisible();

    // Étape localisation : adresse + clic sur la carte
    await page.getByTestId("wizard-step-location").click();
    await page.getByTestId("wizard-address").fill("5 rue des Jasmins, Ghazela");
    const map = page.getByTestId("location-picker");
    await expect(map).toBeVisible();
    await map.click({ position: { x: 200, y: 140 } });
    await expect(page.getByText(/Position : /)).toBeVisible();
    await page.getByTestId("wizard-save-location").click();
    await expect(page.getByText("Enregistré.").first()).toBeVisible();

    // Étape photos : 3 fichiers
    await page.getByTestId("wizard-step-photos").click();
    const png = await pngBuffer();
    await page.getByTestId("photo-input").setInputFiles([
      { name: "salon.png", mimeType: "image/png", buffer: png },
      { name: "chambre.png", mimeType: "image/png", buffer: png },
      { name: "cuisine.png", mimeType: "image/png", buffer: png },
    ]);
    await expect(page.getByTestId("photo-item")).toHaveCount(3, { timeout: 30_000 });

    // Étape tarifs : mensuel
    await page.getByTestId("wizard-step-pricing").click();
    await page.getByTestId("plan-monthly-toggle").click();
    await page.getByTestId("plan-monthly-price").fill("950");
    await page.getByTestId("plan-monthly-save").click();
    await expect(page.getByText("Tarif mois enregistré.")).toBeVisible();

    // Publication
    await page.getByTestId("wizard-step-publish").click();
    await expect(page.getByText("L'annonce est complète.")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("wizard-submit").click();
    await expect(page.getByText("Annonce en attente de validation.")).toBeVisible({
      timeout: 15_000,
    });

    // Visible dans « Mes biens » avec le bon statut
    await gotoReady(page, "/hote/biens");
    const row = page.getByTestId("host-property-row").filter({ hasText: title });
    await expect(row).toBeVisible();
    await expect(row).toContainText("En attente de validation");
  });

  test("un voyageur ne peut pas accéder à l'espace propriétaire", async ({ page }) => {
    await login(page, ACCOUNTS.traveler);
    await gotoReady(page, "/hote");
    await expect(page).toHaveURL(/^http:\/\/[^/]+\/$/, { timeout: 15_000 });
  });
});
