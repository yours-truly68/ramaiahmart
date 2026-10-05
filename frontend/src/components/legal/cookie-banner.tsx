"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Cookie, SlidersHorizontal } from "lucide-react";
import {
  getStoredConsent,
  acceptAll,
  acceptOnlyNecessary,
  openCookiePreferencesModal,
  CONSENT_UPDATED_EVENT,
} from "@/lib/cookie-consent";

export function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const stored = getStoredConsent();
    if (!stored) {
      const timer = setTimeout(() => setVisible(true), 500);
      return () => clearTimeout(timer);
    }
  }, []);

  useEffect(() => {
    const handleUpdate = () => {
      setVisible(false);
    };
    window.addEventListener(CONSENT_UPDATED_EVENT, handleUpdate);
    return () => window.removeEventListener(CONSENT_UPDATED_EVENT, handleUpdate);
  }, []);

  if (!visible) return null;

  const handleOnlyNecessary = () => {
    acceptOnlyNecessary();
    setVisible(false);
  };

  const handleAcceptAll = () => {
    acceptAll();
    setVisible(false);
  };

  return (
    <aside
      className="cookie-banner-wrapper"
      role="region"
      aria-label="Cookie consent banner"
    >
      <div className="cookie-banner-card rm-container">
        <div className="cookie-banner-content">
          <div className="cookie-banner-icon-badge" aria-hidden="true">
            <Cookie size={20} />
          </div>
          <div className="cookie-banner-text">
            <h2 className="cookie-banner-title">We value your campus privacy</h2>
            <p className="cookie-banner-desc">
              Strictly necessary cookies are required to authenticate your verified{" "}
              <strong>@msrit.edu</strong> student account and keep sessions secure. Optional
              performance cookies help us understand usage. We never sell your personal data.
              Learn more in our{" "}
              <Link href="/privacy" className="cookie-link">
                Privacy Policy
              </Link>{" "}
              and{" "}
              <Link href="/terms" className="cookie-link">
                Terms of Service
              </Link>
              .
            </p>
          </div>
        </div>

        <div className="cookie-banner-actions">
          <button
            type="button"
            className="cookie-btn cookie-btn-subtle"
            onClick={handleOnlyNecessary}
          >
            Only Necessary
          </button>
          <button
            type="button"
            className="cookie-btn cookie-btn-outline"
            onClick={openCookiePreferencesModal}
          >
            <SlidersHorizontal size={14} aria-hidden="true" />
            <span>Manage Preferences</span>
          </button>
          <button
            type="button"
            className="cookie-btn cookie-btn-accent"
            onClick={handleAcceptAll}
          >
            Accept Optional
          </button>
        </div>
      </div>
    </aside>
  );
}
