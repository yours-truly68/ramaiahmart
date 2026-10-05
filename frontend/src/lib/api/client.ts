export class ApiError extends Error {
  constructor(public status: number, public code = "REQUEST_FAILED") { super("The request could not be completed."); }
}
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/market/${path}`, { ...options, headers: { "Content-Type": "application/json", ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    if (response.status === 401 && !path.startsWith("auth/") && typeof window !== "undefined") window.dispatchEvent(new Event("ramaiah:unauthorized"));
    throw new ApiError(response.status, body?.error?.code);
  }
  return response.json() as Promise<T>;
}
export function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "We couldn’t connect. Please try again.";
  const messages: Record<string, string> = {
    INVALID_CREDENTIALS: "That email and password don’t match. Please try again.",
    EMAIL_ALREADY_EXISTS: "There’s already an account with this email. Try logging in.",
    INVALID_UNIVERSITY_EMAIL: "Use an email from one of the supported university domains.",
    INVALID_OR_EXPIRED_CODE: "That code is incorrect or has expired. Please check your code.",
    FORBIDDEN_UNVERIFIED: "Verify your university email before submitting your post.",
    USER_INACTIVE: "This account is inactive. You can’t continue with this account.",
    VALIDATION_ERROR: "Please check the fields and try again.",
    CATEGORY_NOT_FOUND: "That category is no longer available. Choose another category.",
    POST_NOT_FOUND: "This post is no longer available.",
    LOGOUT_UNAVAILABLE: "We couldn’t end your session. Please try logging out again.",
  };
  return messages[error.code] ?? (error.status === 401 ? "Your session has expired. Log in again to continue." : "We couldn’t complete that request. Please try again.");
}
