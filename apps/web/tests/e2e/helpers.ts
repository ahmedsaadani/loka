import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const API_URL = process.env.E2E_API_URL ?? "http://localhost:18000/api/v1";

export const ACCOUNTS = {
  admin: { email: "admin@loka.tn", password: "loka-admin" },
  staff: { email: "staff@loka.tn", password: "loka-staff" },
  host: { email: "host@loka.tn", password: "loka-host" },
  traveler: { email: "traveler@loka.tn", password: "loka-traveler" },
} as const;

/** Navigue puis attend l'hydratation React (le serveur de dev est lent au premier rendu). */
export async function gotoReady(page: Page, url: string) {
  await page.goto(url);
  await page.waitForSelector("html[data-hydrated]", { timeout: 60_000 });
}

/** Connexion via le formulaire ; attend la redirection hors de /connexion. */
export async function login(
  page: Page,
  account: { email: string; password: string },
  next?: string,
) {
  await gotoReady(page, next ? `/connexion?next=${encodeURIComponent(next)}` : "/connexion");
  await page.getByTestId("login-email").fill(account.email);
  await page.getByTestId("login-password").fill(account.password);
  await page.getByTestId("login-submit").click();
  await expect(page).not.toHaveURL(/\/connexion/, { timeout: 60_000 });
}

/** Jeton d'accès via l'API (pour préparer des données de test). */
export async function apiToken(
  request: APIRequestContext,
  account: { email: string; password: string },
): Promise<string> {
  const response = await request.post(`${API_URL}/auth/login/`, { data: account });
  expect(response.ok(), `login API ${account.email}`).toBeTruthy();
  const body = (await response.json()) as { access: string };
  return body.access;
}

export function isoDate(daysFromNow: number): string {
  const d = new Date();
  d.setDate(d.getDate() + daysFromNow);
  return d.toISOString().slice(0, 10);
}

/** PNG 64x48 valide (généré à la volée) pour les uploads. */
export async function pngBuffer(): Promise<Buffer> {
  const { deflateSync } = await import("node:zlib");
  const width = 64;
  const height = 48;
  const raw = Buffer.alloc((width * 3 + 1) * height);
  for (let y = 0; y < height; y += 1) {
    raw[y * (width * 3 + 1)] = 0;
    for (let x = 0; x < width; x += 1) {
      const i = y * (width * 3 + 1) + 1 + x * 3;
      raw[i] = 184;
      raw[i + 1] = 85;
      raw[i + 2] = 46;
    }
  }
  const crcTable = Array.from({ length: 256 }, (_, n) => {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  });
  const crc32 = (buf: Buffer) => {
    let c = 0xffffffff;
    for (const b of buf) c = crcTable[(c ^ b) & 0xff]! ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  };
  const chunk = (type: string, data: Buffer) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const typeData = Buffer.concat([Buffer.from(type, "ascii"), data]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(typeData));
    return Buffer.concat([len, typeData, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = 2;
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    chunk("IDAT", deflateSync(raw)),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

/** Crée via l'API un bien complet (photos, tarif) et le soumet à validation. Retourne son public_id. */
export async function createSubmittedProperty(
  request: APIRequestContext,
  token: string,
  title: string,
): Promise<string> {
  const headers = { Authorization: `Bearer ${token}` };
  const created = await request.post(`${API_URL}/listings/host/properties/`, {
    headers,
    data: {
      title,
      description: "Appartement de test créé par Playwright. ".repeat(3),
      property_type: "apartment",
      rooms_label: "S+2",
      bedrooms: 2,
      bathrooms: 1,
      surface_m2: 80,
      max_guests: 4,
      city: "ariana",
      neighborhood: "ghazela",
      address_private: "12 rue de test, Ghazela",
      location: { lat: 36.8975, lng: 10.1875 },
    },
  });
  expect(created.ok(), await created.text()).toBeTruthy();
  const property = (await created.json()) as { public_id: string };
  const png = await pngBuffer();
  for (let i = 0; i < 3; i += 1) {
    const upload = await request.post(
      `${API_URL}/listings/host/properties/${property.public_id}/photos/`,
      {
        headers,
        multipart: {
          image: { name: `photo-${i}.png`, mimeType: "image/png", buffer: png },
          alt_text: `Photo ${i + 1}`,
        },
      },
    );
    expect(upload.ok(), await upload.text()).toBeTruthy();
  }
  const pricing = await request.post(
    `${API_URL}/listings/host/properties/${property.public_id}/pricing/`,
    {
      headers,
      data: { rental_mode: "monthly", price: "900.00", min_duration: 1 },
    },
  );
  expect(pricing.ok()).toBeTruthy();
  const submitted = await request.post(
    `${API_URL}/listings/host/properties/${property.public_id}/submit/`,
    { headers },
  );
  expect(submitted.ok(), await submitted.text()).toBeTruthy();
  return property.public_id;
}
