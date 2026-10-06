import { NextResponse, type NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const isDev = process.env.NODE_ENV !== "production";

  // Production forbids unsafe-eval. In development, webpack / Fast Refresh requires unsafe-eval.
  const scriptSrc = isDev
    ? `'self' 'unsafe-eval' 'nonce-${nonce}'`
    : `'self' 'nonce-${nonce}' 'strict-dynamic'`;

  // Content Security Policy
  const cspHeader = `
    default-src 'self';
    script-src ${scriptSrc};
    style-src 'self' 'unsafe-inline';
    img-src 'self' blob: data: https: http://localhost:9100 http://127.0.0.1:9100;
    font-src 'self';
    connect-src 'self' https: http://localhost:8000 http://127.0.0.1:8000 http://localhost:9100 http://127.0.0.1:9100;
    frame-src 'none';
    object-src 'none';
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'none';
  `
    .replace(/\s{2,}/g, " ")
    .trim();

  // Set request headers so Next.js reads x-nonce for inline script generation
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", cspHeader);

  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });

  // Set the authoritative Content-Security-Policy header on the response
  response.headers.set("Content-Security-Policy", cspHeader);

  return response;
}

export const config = {
  matcher: [
    {
      source:
        "/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|woff2?)$).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
