"use client";

import { useEffect, useState, useRef } from "react";
import { ShieldCheck, X } from "lucide-react";
import {
  getStoredConsent,
  saveConsent,
  acceptAll,
  acceptOnlyNecessary,
  OPEN_COOKIE_MODAL_EVENT,
} from "@/lib/cookie-consent";

export function CookieModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const handleOpen = () => {
      const stored = getStoredConsent();
      setAnalytics(stored?.analytics ?? false);
      setMarketing(stored?.marketing ?? false);
      setIsOpen(true);
    };

    window.addEventListener(OPEN_COOKIE_MODAL_EVENT, handleOpen);
    return () => window.removeEventListener(OPEN_COOKIE_MODAL_EVENT, handleOpen);
  }, []);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
      closeButtonRef.current?.focus();

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          setIsOpen(false);
        }
      };

      window.addEventListener("keydown", handleKeyDown);
      return () => {
        document.body.style.overflow = "";
        window.removeEventListener("keydown", handleKeyDown);
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = () => {
    saveConsent({
      necessary: true,
      analytics,
      marketing,
    });
    setIsOpen(false);
  };

  const handleAcceptAll = () => {
    acceptAll();
    setIsOpen(false);
  };

  const handleOnlyNecessary = () => {
    acceptOnlyNecessary();
    setIsOpen(false);
  };

  return (
    <div
      className="cookie-modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) setIsOpen(false);
      }}
    >
      <div
        ref={modalRef}
        className="cookie-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cookie-modal-title"
        aria-describedby="cookie-modal-desc"
      >
        <div className="cookie-modal-header">
          <div className="cookie-modal-title-group">
            <span className="cookie-modal-badge">
              <ShieldCheck size={14} aria-hidden="true" />
              <span>Privacy & Controls</span>
            </span>
            <h2 id="cookie-modal-title" className="cookie-modal-title">
              Cookie Preferences
            </h2>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            className="cookie-modal-close"
            onClick={() => setIsOpen(false)}
            aria-label="Close cookie preferences modal"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <p id="cookie-modal-desc" className="cookie-modal-intro">
          We respect your privacy. Strictly necessary cookies ensure authentication and
          campus security. You can customize optional cookies below.
        </p>

        <div className="cookie-categories-list">
          {/* Strictly Necessary */}
          <div className="cookie-cat-item">
            <div className="cookie-cat-header">
              <div className="cookie-cat-info">
                <div className="cookie-cat-title-row">
                  <h3 className="cookie-cat-name">Strictly Necessary</h3>
                  <span className="cookie-pill-always">Always Active</span>
                </div>
                <p className="cookie-cat-desc">
                  Required for RamaiahMart to function. These maintain your authenticated student
                  session (<code className="cookie-code">ramaiahmart_access</code>,{" "}
                  <code className="cookie-code">ramaiahmart_refresh</code>), secure request handling,
                  and remember your cookie preferences.
                </p>
              </div>
            </div>
          </div>

          {/* Analytics / Usage */}
          <div className="cookie-cat-item">
            <div className="cookie-cat-header">
              <div className="cookie-cat-info">
                <div className="cookie-cat-title-row">
                  <h3 className="cookie-cat-name">Analytics & Performance</h3>
                  <label className="cookie-toggle-label">
                    <input
                      type="checkbox"
                      className="cookie-toggle-input"
                      checked={analytics}
                      onChange={(e) => setAnalytics(e.target.checked)}
                      aria-label="Enable analytics cookies"
                    />
                    <span className="cookie-toggle-slider" aria-hidden="true" />
                  </label>
                </div>
                <p className="cookie-cat-desc">
                  Helps us understand student usage patterns to improve search and navigation.
                  <em> Note: RamaiahMart currently loads zero third-party tracking scripts.</em>
                </p>
              </div>
            </div>
          </div>

          {/* Marketing / Advertising */}
          <div className="cookie-cat-item">
            <div className="cookie-cat-header">
              <div className="cookie-cat-info">
                <div className="cookie-cat-title-row">
                  <h3 className="cookie-cat-name">Marketing & Social</h3>
                  <label className="cookie-toggle-label">
                    <input
                      type="checkbox"
                      className="cookie-toggle-input"
                      checked={marketing}
                      onChange={(e) => setMarketing(e.target.checked)}
                      aria-label="Enable marketing cookies"
                    />
                    <span className="cookie-toggle-slider" aria-hidden="true" />
                  </label>
                </div>
                <p className="cookie-cat-desc">
                  Reserved for future campus partner notices. RamaiahMart is an open student
                  initiative and does not display third-party advertisements or sell student data.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="cookie-modal-footer">
          <div className="cookie-modal-actions-left">
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
              onClick={handleAcceptAll}
            >
              Accept All
            </button>
          </div>
          <button
            type="button"
            className="cookie-btn cookie-btn-accent"
            onClick={handleSave}
          >
            Save Preferences
          </button>
        </div>
      </div>
    </div>
  );
}
