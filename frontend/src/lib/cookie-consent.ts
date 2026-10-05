export interface CookiePreferences {
  necessary: boolean;
  analytics: boolean;
  marketing: boolean;
  version: string;
  updated_at: string;
}

export const CONSENT_COOKIE_NAME = "ramaiahmart_cookie_consent";
export const CONSENT_VERSION = "1.0";
export const OPEN_COOKIE_MODAL_EVENT = "ramaiahmart:open-cookie-modal";
export const CONSENT_UPDATED_EVENT = "ramaiahmart:consent-updated";

const DEFAULT_PREFERENCES: CookiePreferences = {
  necessary: true,
  analytics: false,
  marketing: false,
  version: CONSENT_VERSION,
  updated_at: "",
};

export function getStoredConsent(): CookiePreferences | null {
  if (typeof document === "undefined") return null;

  // 1. Try reading cookie
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${CONSENT_COOKIE_NAME}=`));

  if (match) {
    try {
      const parsed = JSON.parse(decodeURIComponent(match.split("=")[1]));
      if (typeof parsed === "object" && parsed !== null && parsed.necessary === true) {
        return parsed as CookiePreferences;
      }
    } catch {
      // Malformed cookie ignored
    }
  }

  // 2. Fallback to localStorage for client consistency
  try {
    const local = localStorage.getItem(CONSENT_COOKIE_NAME);
    if (local) {
      const parsed = JSON.parse(local);
      if (parsed?.necessary === true) {
        return parsed as CookiePreferences;
      }
    }
  } catch {
    // LocalStorage unavailable
  }

  return null;
}

export function saveConsent(preferences: Partial<CookiePreferences>): CookiePreferences {
  const finalPrefs: CookiePreferences = {
    ...DEFAULT_PREFERENCES,
    ...preferences,
    necessary: true, // Strictly necessary is locked on
    version: CONSENT_VERSION,
    updated_at: new Date().toISOString(),
  };

  const serialized = encodeURIComponent(JSON.stringify(finalPrefs));

  if (typeof document !== "undefined") {
    // Cookie valid for 1 year (365 days)
    const maxAge = 365 * 24 * 60 * 60;
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `${CONSENT_COOKIE_NAME}=${serialized}; path=/; max-age=${maxAge}; SameSite=Lax${secure}`;

    try {
      localStorage.setItem(CONSENT_COOKIE_NAME, JSON.stringify(finalPrefs));
    } catch {
      // LocalStorage disabled or quota exceeded
    }

    window.dispatchEvent(
      new CustomEvent(CONSENT_UPDATED_EVENT, { detail: finalPrefs })
    );
  }

  return finalPrefs;
}

export function acceptOnlyNecessary(): CookiePreferences {
  return saveConsent({
    necessary: true,
    analytics: false,
    marketing: false,
  });
}

export function acceptAll(): CookiePreferences {
  return saveConsent({
    necessary: true,
    analytics: true,
    marketing: true,
  });
}

export function openCookiePreferencesModal(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(OPEN_COOKIE_MODAL_EVENT));
  }
}
