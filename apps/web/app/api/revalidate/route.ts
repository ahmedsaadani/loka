import { revalidatePath, revalidateTag } from "next/cache";
import { NextResponse, type NextRequest } from "next/server";

/**
 * Webhook appelé par l'API Django (notifications.tasks.revalidate_front) quand un bien est
 * publié, mis en pause ou re-tarifé. Protégé par un secret partagé.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const secret = process.env.REVALIDATE_SECRET;
  if (!secret || request.headers.get("x-revalidate-secret") !== secret) {
    return NextResponse.json({ detail: "Non autorisé." }, { status: 401 });
  }
  let body: { paths?: unknown; tags?: unknown };
  try {
    body = (await request.json()) as { paths?: unknown; tags?: unknown };
  } catch {
    return NextResponse.json({ detail: "JSON invalide." }, { status: 400 });
  }
  const paths = Array.isArray(body.paths)
    ? body.paths.filter((p): p is string => typeof p === "string" && p.startsWith("/"))
    : [];
  const tags = Array.isArray(body.tags)
    ? body.tags.filter((t): t is string => typeof t === "string")
    : [];
  for (const path of paths.slice(0, 50)) revalidatePath(path);
  for (const tag of tags.slice(0, 50)) revalidateTag(tag);
  return NextResponse.json({ revalidated: { paths: paths.length, tags: tags.length } });
}
