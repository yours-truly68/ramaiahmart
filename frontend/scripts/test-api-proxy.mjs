import assert from "node:assert/strict";

console.log("=== Testing Next.js API Proxy Route Allowlist Security Boundary ===");

const uuidPattern = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
const testUuid = "12345678-1234-5678-1234-567812345678";

function isAllowedRoute(path, method) {
  const isPostId = new RegExp(`^posts/${uuidPattern}$`).test(path);
  const isPostAction = new RegExp(`^posts/${uuidPattern}/(publish|close)$`).test(path);
  const isPostConv = new RegExp(`^posts/${uuidPattern}/conversations$`).test(path);
  const isConvId = new RegExp(`^conversations/${uuidPattern}$`).test(path);
  const isConvMessages = new RegExp(`^conversations/${uuidPattern}/messages$`).test(path);
  const isConvClose = new RegExp(`^conversations/${uuidPattern}/close$`).test(path);
  const isReportId = new RegExp(`^reports/${uuidPattern}$`).test(path);
  const isMediaId = new RegExp(`^media/${uuidPattern}$`).test(path);

  return method === "GET"
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
}

// 1. Verify Required V1 Endpoints are ALLOWED
const requiredRoutes = [
  // Auth
  ["auth/login", "POST"],
  ["auth/register", "POST"],
  ["auth/logout", "POST"],
  ["auth/refresh", "POST"],
  ["auth/config", "GET"],
  // Users
  ["users/me", "GET"],
  ["users/me", "PATCH"],
  ["users/me/posts", "GET"],
  ["users/me/stats", "GET"],
  ["users/me/deletion-request", "POST"],
  ["users/me/deletion-cancel", "POST"],
  // Categories
  ["categories", "GET"],
  // Posts
  ["posts", "GET"],
  [`posts/${testUuid}`, "GET"],
  ["posts", "POST"],
  [`posts/${testUuid}`, "PATCH"],
  [`posts/${testUuid}`, "DELETE"],
  [`posts/${testUuid}/publish`, "POST"],
  [`posts/${testUuid}/close`, "POST"],
  // Media
  ["media/config", "GET"],
  ["media/upload-url", "POST"],
  ["media/complete", "POST"],
  [`media/${testUuid}`, "DELETE"],
  // Conversations
  [`posts/${testUuid}/conversations`, "POST"],
  ["conversations", "GET"],
  [`conversations/${testUuid}`, "GET"],
  [`conversations/${testUuid}/messages`, "GET"],
  [`conversations/${testUuid}/messages`, "POST"],
  [`conversations/${testUuid}/close`, "POST"],
  // Reports
  ["reports", "POST"],
  [`reports/${testUuid}`, "GET"],
  // Legal
  ["legal/documents", "GET"],
  ["legal/documents/terms", "GET"],
  ["legal/documents/privacy", "GET"],
  ["legal/consent-status", "GET"],
  ["legal/consent", "POST"],
];

for (const [path, method] of requiredRoutes) {
  assert.equal(
    isAllowedRoute(path, method),
    true,
    `Required endpoint [${method} ${path}] must be allowed through proxy.`
  );
}
console.log(`✓ All ${requiredRoutes.length} required V1 routes passed allowlist.`);

// 2. Verify Arbitrary / Malicious / Unknown Endpoints are REJECTED (404)
const forbiddenRoutes = [
  ["admin", "GET"],
  ["admin/users", "GET"],
  ["users/other", "GET"],
  ["users/123", "GET"],
  ["posts/invalid-uuid", "GET"],
  ["posts/123/delete", "POST"],
  ["internal/health", "GET"],
  ["eval", "POST"],
  ["auth/reset-password", "POST"],
  ["auth/login", "GET"], // Login only allowed as POST
  ["categories", "POST"], // Categories read-only
  ["categories", "DELETE"],
  ["conversations", "POST"], // Initiating requires posts/{post_id}/conversations
  ["media/upload-url", "GET"], // Upload-url only allowed as POST
  ["reports", "GET"], // Mass reports enumeration not allowed on proxy
  ["system/exec", "POST"],
];

for (const [path, method] of forbiddenRoutes) {
  assert.equal(
    isAllowedRoute(path, method),
    false,
    `Forbidden endpoint [${method} ${path}] must be rejected (404).`
  );
}
console.log(`✓ All ${forbiddenRoutes.length} forbidden/unknown routes were successfully blocked.`);

// 3. Same-Origin Validation Logic
function isSameOrigin(originHeader, hostHeader) {
  try {
    const origin = new URL(originHeader ?? "");
    const host = hostHeader;
    return ["http:", "https:"].includes(origin.protocol) && origin.host === host;
  } catch {
    return false;
  }
}

assert.equal(isSameOrigin("http://localhost:3000", "localhost:3000"), true);
assert.equal(isSameOrigin("https://ramaiahmart.com", "ramaiahmart.com"), true);
assert.equal(isSameOrigin("http://evil.com", "localhost:3000"), false);
assert.equal(isSameOrigin("https://evil.com", "ramaiahmart.com"), false);
assert.equal(isSameOrigin("", "localhost:3000"), false);
assert.equal(isSameOrigin("javascript:void(0)", "localhost:3000"), false);
console.log("✓ Same-origin CSRF validation logic verified.");

console.log("\nALL API PROXY TESTS PASSED!");
