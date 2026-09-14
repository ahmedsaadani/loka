import { expect, test } from "@playwright/test";

import { ACCOUNTS, API_URL, apiToken, gotoReady } from "./helpers";

test.describe("Pages marketing : devenir hôte, comment ça marche, carte regroupée", () => {
  test("le formulaire propriétaire crée un lead visible par l'équipe", async ({
    page,
    request,
  }) => {
    const stamp = Date.now();
    await gotoReady(page, "/devenir-hote");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Louez votre bien");

    const form = page.getByTestId("owner-contact-form");
    await form.getByLabel("Votre nom").fill(`Playwright ${stamp}`);
    await form.getByLabel("Téléphone").fill("+216 20 000 000");
    await form.getByLabel("Ville du bien").fill("Ariana");
    await form.getByLabel("Message (facultatif)").fill("S+2 à Ennasr, test automatisé.");
    await form.getByRole("button", { name: "Être rappelé" }).click();
    await expect(page.getByTestId("owner-contact-success")).toBeVisible();

    const token = await apiToken(request, ACCOUNTS.staff);
    const leads = await request.get(`${API_URL}/leads/?source=manual&page_size=50`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(leads.ok()).toBeTruthy();
    const list = (await leads.json()) as { results: Array<{ title: string; city: string }> };
    const created = list.results.find((l) => l.title.includes(`Playwright ${stamp}`));
    expect(created).toBeTruthy();
    expect(created?.city).toBe("Ariana");
  });

  test("comment ça marche : sections voyageur, vérification et propriétaire", async ({ page }) => {
    await gotoReady(page, "/comment-ca-marche");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Comment ça marche");
    await expect(page.getByRole("heading", { name: "Vous cherchez un logement" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Ce que « vérifié par Loka » veut dire" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Proposer mon bien" }).click();
    await expect(page).toHaveURL(/\/devenir-hote$/);
  });

  test("la carte regroupe les biens proches et dézoome au clic", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name.includes("mobile"), "carte desktop uniquement");
    await gotoReady(page, "/recherche?city=ariana&rental_mode=monthly");
    const map = page.getByRole("region", { name: "Carte des résultats" });
    await expect(map.locator("canvas")).toBeVisible();
    const cluster = map.getByRole("button", { name: /logements, cliquer pour zoomer/ }).first();
    await expect(cluster).toBeVisible({ timeout: 15_000 });
    const before = Number(await cluster.textContent());
    expect(before).toBeGreaterThan(1);
    await cluster.click();
    // Après le zoom, la liste est resynchronisée sur la zone visible (bbox) et le groupe éclate.
    await expect
      .poll(async () => map.getByRole("button", { name: /logements, cliquer/ }).count(), {
        timeout: 10_000,
      })
      .toBeLessThan(await map.getByRole("button").count());
    await expect(page.getByTestId("property-card").first()).toBeVisible();
  });
});
