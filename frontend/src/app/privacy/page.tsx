import type { Metadata } from "next";
import { Lock } from "lucide-react";
import { SiteHeader } from "@/components/marketplace/site-header";
import { SiteFooter } from "@/components/marketplace/site-footer";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description:
    "Official Privacy Policy detailing student data handling, account lifecycle, inactivity, 15-day deletion grace period, and backup policies on RamaiahMart.",
  alternates: {
    canonical: "/privacy",
  },
  openGraph: {
    title: "Privacy Policy — RamaiahMart",
    description:
      "Privacy Policy detailing student data handling and account lifecycle on RamaiahMart.",
    url: "/privacy",
  },
  robots: {
    index: true,
    follow: true,
  },
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
            <h2>1. Platform Operator & Institutional Disclaimer</h2>
            <p>
              RamaiahMart is operated independently by <strong>Mohammad Razim</strong>. For all privacy inquiries,
              account deletion requests, data inquiries, legal notices, platform support, and reports, you can reach
              out directly via email at{" "}
              <a href="mailto:mohammedrazim880@gmail.com" className="cookie-link">
                mohammedrazim880@gmail.com
              </a>
              .
            </p>
            <p>
              <strong>Institutional Disclaimer:</strong> RamaiahMart is an independent student marketplace designed
              for campus peer exchange and is <strong>not affiliated with, owned by, operated by, sponsored by, or
              endorsed by Ramaiah Institute of Technology (MSRIT/RIT)</strong>.
            </p>
            <p>
              <strong>We do not sell student data, rent contact lists, or run third-party behavioral
              advertising networks.</strong>
            </p>
          </section>

          <section className="legal-section">
            <h2>2. Information We Collect</h2>
            <p>We process only data strictly necessary to operate and secure the marketplace:</p>
            <ul>
              <li>
                <strong>Account & Profile Information:</strong> Full name, university email address (e.g.,{" "}
                <code>you@msrit.edu</code>), one-way cryptographic bcrypt password hash (we never store or view
                plaintext passwords), optional biography, and optional profile avatar image.
              </li>
              <li>
                <strong>Marketplace Content:</strong> Post titles, pricing, descriptions, offer/request classifications,
                categories, and uploaded item photographs stored in secure object storage.
              </li>
              <li>
                <strong>Conversations & Messaging:</strong> Direct user-to-user messages and timestamps exchanged within
                the marketplace to facilitate campus item handoffs.
              </li>
              <li>
                <strong>Moderation & Security Information:</strong> Reports submitted regarding suspicious listings,
                safety alerts, and administrative moderation actions taken to safeguard the community.
              </li>
              <li>
                <strong>Verification Data:</strong> Time-limited verification codes (OTPs) dispatched during registration
                to verify academic enrollment, protected with rate limiting and automated invalidation after failed attempts.
              </li>
              <li>
                <strong>Legal & Consent Records:</strong> Records of your explicit acceptance of our Terms & Conditions and
                Privacy Policy (including document versions and acceptance timestamps) as well as your cookie preferences.
              </li>
              <li>
                <strong>Technical & Security Logs:</strong> IP address, user-agent string, request path, timestamp, and HTTP
                response codes. Sensitive fields (passwords, tokens, verification codes) are strictly scrubbed and never logged.
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>3. Cookie Classification & Usage</h2>
            <p>
              Cookies are small data files stored on your browser. RamaiahMart classifies cookies into two distinct tiers:
            </p>
            <ul>
              <li>
                <strong>Strictly Necessary Cookies:</strong> Essential for authentication, session stability, and platform
                security.
                <br />
                Examples: <code className="cookie-code">ramaiahmart_access</code> (short-lived JWT),{" "}
                <code className="cookie-code">ramaiahmart_refresh</code> (long-lived refresh token), and{" "}
                <code className="cookie-code">ramaiahmart_cookie_consent</code> (stores your cookie preferences).
                These cookies use <code>HttpOnly</code>, <code>SameSite=Lax</code>, and <code>Secure</code> flags in production.
              </li>
              <li>
                <strong>Optional Cookies (Analytics & Marketing):</strong> RamaiahMart currently loads{" "}
                <strong>zero third-party tracking scripts, zero Google Analytics, and zero advertising pixels</strong>. We
                provide consent toggles so you can control any future non-essential features via our Cookie Preferences modal.
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>4. Purposes of Processing</h2>
            <p>Your information is processed strictly for the following purposes:</p>
            <ul>
              <li>Operating your account and maintaining secure authenticated sessions.</li>
              <li>Providing marketplace functionality: publishing, editing, searching, and managing listings.</li>
              <li>Enabling user-to-user communication for coordinating item inspections and handoffs.</li>
              <li>Reviewing reported listings and enforcing campus safety rules against fraud or abuse.</li>
              <li>Protecting the platform through network-level and application-level rate limiting.</li>
              <li>Troubleshooting technical defects and improving service stability.</li>
              <li>Complying with applicable legal, security, and dispute obligations.</li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>5. Account Inactivity Policy (Non-Destructive)</h2>
            <p>
              RamaiahMart does <strong>not</strong> automatically delete your account or destroy your data solely because
              you have been inactive.
            </p>
            <p>
              If an account experiences no meaningful activity (such as logging in, publishing or editing a listing, or sending a
              message) for approximately <strong>90 days</strong>, it may be marked as <code>INACTIVE</code>. An inactive account:
            </p>
            <ul>
              <li>Is NOT deleted or suspended.</li>
              <li>Does NOT lose any posts, messages, or account history.</li>
              <li>Incurs no penalty or loss of access.</li>
              <li>Can return normally at any time. Performing any meaningful authenticated activity immediately restores your account to <code>ACTIVE</code> status.</li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>6. User-Requested Account Deletion & 15-Day Grace Period</h2>
            <p>
              You have the right to request deletion of your account at any time through your Profile Settings or by emailing{" "}
              <a href="mailto:mohammedrazim880@gmail.com" className="cookie-link">
                mohammedrazim880@gmail.com
              </a>
              .
            </p>
            <p>
              When you submit an account deletion request:
            </p>
            <ul>
              <li>
                <strong>15-Day Grace Period:</strong> Your account enters a <code>DELETION_PENDING</code> state for exactly 15 days.
                Your account is not destroyed immediately.
              </li>
              <li>
                <strong>Automatic Cancellation on Activity:</strong> If you log in or perform any qualifying authenticated activity
                during this 15-day grace period, your deletion request is automatically cancelled, and your account returns to{" "}
                <code>ACTIVE</code> status. You may also click &ldquo;Cancel deletion&rdquo; in your profile settings.
              </li>
              <li>
                <strong>Permanent Deletion:</strong> After 15 days without qualifying activity, your account and all associated
                production records (user profile, listings, post images, conversations, and messages) are permanently and
                irreversibly deleted from the active production database and object storage.
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>7. Disaster-Recovery Backups & Retention</h2>
            <p>
              RamaiahMart maintains limited rolling backups strictly for disaster recovery, business continuity, and system restoration.
            </p>
            <ul>
              <li>
                <strong>7-Day Retention:</strong> Backups follow a rolling 7-day retention schedule. Backups older than 7 days are
                automatically retired and pruned.
              </li>
              <li>
                <strong>Reconciliation on Synchronization:</strong> Backups mirror current authoritative production data. When an account
                is permanently deleted from production, it is omitted from the subsequent scheduled backup generation.
              </li>
              <li>
                <strong>Backup Latency:</strong> Disaster-recovery backup archives may temporarily retain copies of permanently deleted
                information until the next scheduled backup generation and rotation cycle completes.
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>8. User-to-User Transactions Disclaimer</h2>
            <p>
              RamaiahMart provides an informational discovery and communication platform for campus members. RamaiahMart is not a buyer,
              seller, lender, renter, tenant, tutor, service provider, broker, or party to any transaction negotiated between users.
              Users are solely responsible for inspecting items, verifying counterparties, and conducting handoffs safely in person.
            </p>
          </section>

          <section className="legal-section">
            <h2>9. Contact & Inquiries</h2>
            <p>
              For any questions, rights requests, data concerns, or support, please contact the platform maintainer directly:
            </p>
            <p>
              <strong>Mohammad Razim</strong>
              <br />
              Email:{" "}
              <a href="mailto:mohammedrazim880@gmail.com" className="cookie-link">
                mohammedrazim880@gmail.com
              </a>
            </p>
          </section>
        </article>
      </main>
      <SiteFooter />
    </>
  );
}
