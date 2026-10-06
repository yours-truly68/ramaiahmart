import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const base = (
  process.env.API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");
const accessName = "ramaiahmart_access";
const refreshName = "ramaiahmart_refresh";
const cookieOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  path: "/",
};
type Tokens = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
};
function expiry(token: string): number {
  // Used only for cookie lifetime. FastAPI verifies identity/signatures.
  try {
    return (
      JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString())
        .exp ?? 0
    );
  } catch {
    return 0;
  }
}
const response = (data: unknown, status = 200) =>
  NextResponse.json(data, { status, headers: { "Cache-Control": "no-store" } });

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const path = (await context.params).path.join("/");
  const method = request.method;
  // Explicit UUID pattern matching standard 8-4-4-4-12 hex UUID format
  const uuidPattern = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
  const isPostId = new RegExp(`^posts/${uuidPattern}$`).test(path);
  const isPostAction = new RegExp(`^posts/${uuidPattern}/(publish|close)$`).test(path);
  const isPostConv = new RegExp(`^posts/${uuidPattern}/conversations$`).test(path);
  const isConvId = new RegExp(`^conversations/${uuidPattern}$`).test(path);
  const isConvMessages = new RegExp(`^conversations/${uuidPattern}/messages$`).test(path);
  const isConvClose = new RegExp(`^conversations/${uuidPattern}/close$`).test(path);
  const isReportId = new RegExp(`^reports/${uuidPattern}$`).test(path);
  const isMediaId = new RegExp(`^media/${uuidPattern}$`).test(path);

  const allowed =
    method === "GET"
      ? path === "categories" ||
        path === "posts" ||
        isPostId ||
        path === "users/me" ||
        path === "users/me/posts" ||
        path === "users/me/stats" ||
        path === "auth/config" ||
        path === "media/config" ||
        path === "conversations" ||
        isConvId ||
        isConvMessages ||
        isReportId ||
        path === "legal/documents" ||
        /^legal\/documents\/[A-Za-z0-9_-]+$/.test(path) ||
        path === "legal/consent-status"
      : method === "POST"
        ? path === "auth/login" ||
          path === "auth/register" ||
          path === "auth/logout" ||
          path === "auth/refresh" ||
          path === "posts" ||
          isPostAction ||
          isPostConv ||
          isConvMessages ||
          isConvClose ||
          path === "media/upload-url" ||
          path === "media/complete" ||
          path === "reports" ||
          path === "legal/consent" ||
          path === "users/me/deletion-request" ||
          path === "users/me/deletion-cancel"
        : method === "PATCH"
          ? path === "users/me" || isPostId
          : method === "DELETE" && (isPostId || isMediaId);
  if (!allowed) return response({ error: { code: "NOT_FOUND" } }, 404);
  if (method !== "GET") {
    let sameOrigin = false;
    try {
      const origin = new URL(request.headers.get("origin") ?? "");
      const host =
        request.headers.get("x-forwarded-host") || request.headers.get("host");
      sameOrigin =
        ["http:", "https:"].includes(origin.protocol) && origin.host === host;
    } catch {
      /* Reject missing/malformed origins. */
    }
    if (!sameOrigin)
      return response({ error: { code: "INVALID_ORIGIN" } }, 403);
  }
  const jar = await cookies();
  let access = jar.get(accessName)?.value;
  const refresh = jar.get(refreshName)?.value;
  const clear = () => {
    jar.delete(accessName);
    jar.delete(refreshName);
  };
  const setTokens = (tokens: Tokens) => {
    access = tokens.access_token;
    jar.set(accessName, tokens.access_token, {
      ...cookieOptions,
      maxAge: tokens.expires_in,
    });
    jar.set(refreshName, tokens.refresh_token, {
      ...cookieOptions,
      maxAge: Math.max(
        0,
        expiry(tokens.refresh_token) - Math.floor(Date.now() / 1000),
      ),
    });
  };
  const upstream = (
    target: string,
    verb: string,
    body?: string,
    token?: string,
  ) =>
    fetch(`${base}/${target}`, {
      method: verb,
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      ...(body ? { body } : {}),
    });
  async function renew() {
    if (!refresh) return false;
    const res = await upstream(
      "auth/refresh",
      "POST",
      JSON.stringify({ refresh_token: refresh }),
    );
    if (res.ok) {
      setTokens(await res.json());
      return true;
    }
    if (res.status === 401 || res.status === 403) {
      clear();
      return false;
    }
    throw new Error("Session service unavailable");
  }
  try {
    if (path === "auth/logout") {
      if (refresh) {
        const loggedOut = await upstream(
          "auth/logout",
          "POST",
          JSON.stringify({ refresh_token: refresh }),
        );
        if (!loggedOut.ok)
          return response({ error: { code: "LOGOUT_UNAVAILABLE" } }, 503);
      }
      clear();
      return response({ success: true });
    }
    const isAuth = path.startsWith("auth/");
    let renewed = false;
    if (
      !isAuth &&
      refresh &&
      (!access || expiry(access) <= Date.now() / 1000 + 10)
    ) {
      renewed = await renew();
      if (!renewed) access = undefined;
    }
    const body =
      method === "POST" || method === "PATCH"
        ? await request.text()
        : undefined;
    let res = await upstream(
      `${path}${request.nextUrl.search}`,
      method,
      body,
      isAuth ? undefined : access,
    );
    if (res.status === 401 && !isAuth && !renewed && (await renew())) {
      res = await upstream(
        `${path}${request.nextUrl.search}`,
        method,
        body,
        access,
      );
    }
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      if (res.status === 401 && !isAuth) clear();
      // Pass only machine codes, never raw backend messages or traces.
      const code =
        typeof error?.error?.code === "string" &&
        /^[A-Z_]+$/.test(error.error.code)
          ? error.error.code
          : "REQUEST_FAILED";
      return response({ error: { code } }, res.status);
    }
    if (res.status === 204) return new NextResponse(null, { status: 204 });
    const data = await res.json().catch(() => ({}));
    if (path === "auth/login" || path === "auth/refresh") {
      setTokens(data);
      return response({ success: true });
    }
    return response(data, res.status);
  } catch {
    return response({ error: { code: "SERVICE_UNAVAILABLE" } }, 503);
  }
}
export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
