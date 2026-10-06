/**
 * URL safety validation utilities.
 * Protects against open redirects, JavaScript URI execution, and unexpected schemes.
 */

/**
 * Validates that a string is a safe HTTPS WhatsApp Click-to-Chat URL.
 * Only allows https://wa.me/<digits>?text=...
 */
export function isSafeWhatsAppUrl(url: string | null | undefined): boolean {
  if (!url || typeof url !== "string") return false;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:") return false;
    if (parsed.hostname !== "wa.me") return false;
    // Pathname must be a slash followed by 7-15 digits
    if (!/^\/\d{7,15}$/.test(parsed.pathname)) return false;
    // No usernames/passwords embedded in URL
    if (parsed.username || parsed.password) return false;
    return true;
  } catch {
    return false;
  }
}

/**
 * Validates that an image or resource URL uses safe HTTP or HTTPS protocol.
 * Rejects javascript:, data:, vbscript:, file:, etc.
 */
export function isSafeHttpUrl(url: string | null | undefined): boolean {
  if (!url || typeof url !== "string") return false;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}

/**
 * Validates and sanitizes internal next-destination redirect paths.
 * Prevents open redirects via protocol-relative URLs (//evil.com),
 * backslashes (/\evil.com), control characters, and auth-loop destinations.
 */
export function safeNextPath(
  value: string | null | undefined,
  fallback = "/profile"
): string {
  if (!value || typeof value !== "string") return fallback;
  const trimmed = value.trim();

  // Must begin with a single slash, followed by non-slash and non-backslash
  if (!/^\/(?!\/|[\\/])/.test(trimmed)) return fallback;

  // Reject backslashes and control characters
  if (/[\\\u0000-\u001f\u007f-\u009f]/.test(trimmed)) return fallback;

  // Reject redirects back into login or register to avoid loops
  if (/^\/(login|register)([/?#]|$)/.test(trimmed)) return fallback;

  return trimmed;
}
