import { expect, test } from "@playwright/test";

import { ACCOUNTS, apiToken, createSubmittedProperty, gotoReady, login } from "./helpers";

test.describe("Parcours équipe : validation d'un bien", () => {
  test("publie un bien soumis depuis la file de validation", async ({ page, request }) => {
    const title = `Validation Playwright ${Date.now()}`;
    const hostToken = await apiToken(request, ACCOUNTS.host);
    const publicId = await createSubmittedProperty(request, hostToken, title);

    await login(page, ACCOUNTS.admin);
    await gotoReady(page, "/admin/validation?status=pending_review");
    const row = page.getByTestId("validation-row").filter({ hasText: title });
    await expect(row).toBeVisible({ timeout: 15_000 });
    await row.getByRole("link").first().click();
    await expect(page).toHaveURL(new RegExp(`/admin/biens/${publicId}`));

    // L'adresse exacte est visible pour l'équipe
    await expect(page.getByText("12 rue de test, Ghazela")).toBeVisible();

    await page.getByTestId("admin-publish").click();
    await page.getByTestId("admin-publish-confirm").click();
    await expect(page.getByText("Publié").first()).toBeVisible({ timeout: 15_000 });

    // La fiche publique répond et n'expose pas l'adresse exacte
    const publicPage = await request.get(
      `${process.env.E2E_API_URL ?? "http://localhost:18000/api/v1"}/listings/properties/?page_size=50`,
    );
    const list = (await publicPage.json()) as { results: Array<{ slug: string; title: string }> };
    const published = list.results.find((p) => p.title === title);
    expect(published).toBeTruthy();
    await gotoReady(page, `/logement/${published!.slug}`);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(title);
    await expect(page.getByText("12 rue de test")).toHaveCount(0);
  });

  test("un hôte ne peut pas accéder au back-office", async ({ page }) => {
    await login(page, ACCOUNTS.host);
    await gotoReady(page, "/admin");
    await expect(page).toHaveURL(/^http:\/\/[^/]+\/$/, { timeout: 15_000 });
  });
});
