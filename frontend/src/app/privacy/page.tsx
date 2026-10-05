import type { Metadata } from "next";
import { Lock } from "lucide-react";
import { SiteHeader } from "@/components/marketplace/site-header";
import { SiteFooter } from "@/components/marketplace/site-footer";

export const metadata: Metadata = {
  title: "Privacy Policy — RamaiahMart",
  description:
    "Official Privacy Policy detailing student data handling, university verification, cookie usage, and storage security on RamaiahMart.",
};

export default function PrivacyPage() {
  return (
    <>
      <SiteHeader />
      <main id="main" className="legal-page rm-container">
        <header className="legal-header">
          <div className="legal-kicker">
            <Lock size={16} aria-hidden="true" />
            <span>Data Transparency</span>
          </div>
          <h1 className="legal-title">Privacy Policy</h1>
          <div className="legal-meta">
            <span className="legal-version-badge">Version 1.0</span>
            <span>Effective Date: October 2026</span>
          </div>
        </header>

        <article className="legal-content-body">
          <section className="legal-section">
            <h2>1. Overview & Commitment</h2>
            <p>
              RamaiahMart is designed to connect students of Ramaiah Institute of Technology (MSRIT)
              for safe, peer-to-peer campus exchanges. We believe in minimal data collection: we
              collect only what is strictly required to verify student identity, safeguard the campus
              community from scammers, and enable peer discovery.
            </p>
            <p>
              <strong>We do not sell student data, rent contact lists, or run third-party behavioral
              advertising networks.</strong>
            </p>
            <div className="legal-review-callout">
              <span className="legal-review-tag">[REVIEW REQUIRED: institutional affiliation status]</span>
              <p>
                RamaiahMart is an open student platform developed for Ramaiah Institute of Technology
                students. Formal data sharing agreements with the university administration (MSRIT)
                are subject to institutional review.
              </p>
            </div>
          </section>

          <section className="legal-section">
            <h2>2. Information We Collect</h2>
            <p>We process the following categories of information:</p>
            <ul>
              <li>
                <strong>Identity & Account Data:</strong> Your full name, university email address
                (e.g., <code>you@msrit.edu</code>), password (stored as a one-way cryptographic bcrypt
                hash; we never store or see your plaintext password), optional profile biography,
                and optional avatar image.
              </li>
              <li>
                <strong>Verification Data:</strong> 6-digit one-time verification codes (OTPs)
                dispatched to confirm university enrollment. OTP codes are rate-limited, expire after
                a set window, and are invalidated after 5 failed attempts.
              </li>
              <li>
                <strong>Marketplace Content:</strong> Post titles, pricing, descriptions, offer/request
                classifications, categories, and item photos uploaded to secure S3-compatible object
                storage.
              </li>
              <li>
                <strong>Technical & Access Logs:</strong> IP address, user-agent string, request
                paths, timestamps, HTTP status codes, and unique request identifiers. All server
                logs are strictly sanitized: passwords, authentication tokens, and OTPs are never
                written to log files.
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>3. Cookie Classification & Usage</h2>
            <p>
              Cookies are small files stored on your browser. RamaiahMart classifies cookies into
              two distinct tiers:
            </p>
            <ul>
              <li>
                <strong>Strictly Necessary Cookies:</strong> Essential for authentication, session
                stability, and platform security.
                <br />
                Examples: <code className="cookie-code">ramaiahmart_access</code> (short-lived JWT),{" "}
                <code className="cookie-code">ramaiahmart_refresh</code> (long-lived refresh token),
                and <code className="cookie-code">ramaiahmart_cookie_consent</code> (persists your
                cookie consent preferences). These cookies use <code>HttpOnly</code>,{" "}
                <code>SameSite=Lax</code>, and <code>Secure</code> flags in production.
              </li>
              <li>
                <strong>Optional Cookies (Analytics & Marketing):</strong> RamaiahMart currently
                loads <strong>zero third-party tracking scripts, zero Google Analytics, and zero
                social media pixels</strong>. We provide preference toggles so you can control any
                future non-essential features via our Cookie Preferences modal.
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>4. How We Use Your Information</h2>
            <p>Your information is used strictly to:</p>
            <ul>
              <li>Authenticate your account and maintain your student session.</li>
              <li>Verify that listings originate from active members of the campus community.</li>
              <li>Publish and display your marketplace offerings and requests to other students.</li>
              <li>Moderate listings to prevent fraud, stolen goods, and platform abuse.</li>
              <li>Protect campus users via network-level and application-level rate limiting.</li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>5. Data Storage, Security & Retention</h2>
            <p>
              Data is stored in isolated PostgreSQL database containers and encrypted object
              storage. All external web traffic is encrypted via Transport Layer Security (TLS/HTTPS)
              through our Nginx reverse proxy.
            </p>
            <div className="legal-review-callout">
              <span className="legal-review-tag">[REVIEW REQUIRED: retention period]</span>
              <p>
                Specific data retention periods for closed listings, chat transcripts (when
                implemented), and deactivated student accounts must be finalized in conjunction with
                institutional policies and campus data governance guidelines.
              </p>
            </div>
          </section>

          <section className="legal-section">
            <h2>6. Your Privacy Rights</h2>
            <p>As a student user, you have the right to:</p>
            <ul>
              <li>View and update your personal profile information at any time via your account settings.</li>
              <li>Close, edit, or remove your marketplace listings when an exchange is complete.</li>
              <li>Inspect and adjust your cookie preferences at any time from the site footer.</li>
              <li>Request deactivation of your account and deletion of your profile data.</li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>7. Contact & Privacy Requests</h2>
            <p>
              If you have questions about this Privacy Policy or wish to exercise your data rights:
            </p>
            <ul>
              <li>
                Developer & Maintainer:{" "}
                <a href="mailto:mohammedrazim880@gmail.com" className="cookie-link">
                  mohammedrazim880@gmail.com
                </a>
              </li>
              <li>
                Campus Grievance Officer:{" "}
                <span className="legal-review-tag">
                  [REVIEW REQUIRED: legal entity / grievance officer contact]
                </span>
              </li>
            </ul>
          </section>
        </article>
      </main>
      <SiteFooter />
    </>
  );
}
