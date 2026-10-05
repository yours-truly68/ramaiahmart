import type { Metadata } from "next";
import Link from "next/link";
import { FileText } from "lucide-react";
import { SiteHeader } from "@/components/marketplace/site-header";
import { SiteFooter } from "@/components/marketplace/site-footer";

export const metadata: Metadata = {
  title: "Terms & Conditions — RamaiahMart",
  description:
    "Terms of Service governing student access, marketplace exchange rules, peer transactions, and conduct on RamaiahMart.",
};

export default function TermsPage() {
  return (
    <>
      <SiteHeader />
      <main id="main" className="legal-page rm-container">
        <header className="legal-header">
          <div className="legal-kicker">
            <FileText size={16} aria-hidden="true" />
            <span>Platform Agreement</span>
          </div>
          <h1 className="legal-title">Terms & Conditions</h1>
          <div className="legal-meta">
            <span className="legal-version-badge">Version 1.0</span>
            <span>Effective Date: October 2026</span>
          </div>
        </header>

        <article className="legal-content-body">
          <section className="legal-section">
            <h2>1. Introduction & Campus Scope</h2>
            <p>
              Welcome to <strong>RamaiahMart</strong>. RamaiahMart is an open, hyper-local peer-to-peer
              exchange platform designed specifically for students, faculty, and alumni of Ramaiah
              Institute of Technology (MSRIT), Bengaluru.
            </p>
            <p>
              By accessing RamaiahMart or registering an account, you agree to comply with and be
              bound by these Terms & Conditions and our{" "}
              <Link href="/privacy" className="cookie-link">
                Privacy Policy
              </Link>
              . If you do not agree to these terms, you may not create an account or publish listings
              on the platform.
            </p>
            <div className="legal-review-callout">
              <span className="legal-review-tag">[REVIEW REQUIRED: institutional affiliation status]</span>
              <p>
                RamaiahMart is an independent student-led open campus initiative engineered to serve
                the MSRIT campus. Official university endorsement, partnership status, or formal
                disciplinary jurisdiction must be confirmed with institutional administration.
              </p>
            </div>
          </section>

          <section className="legal-section">
            <h2>2. Account Eligibility & University Verification</h2>
            <ul>
              <li>
                <strong>Eligible Domains:</strong> Account registration is strictly restricted to
                individuals possessing an authorized university email address (such as{" "}
                <code>@msrit.edu</code>).
              </li>
              <li>
                <strong>Email Verification:</strong> To publish posts or initiate exchanges, users
                must complete university email verification using a 6-digit one-time password (OTP).
                Verification codes expire after a set time limit and allow up to 5 attempts before
                invalidation.
              </li>
              <li>
                <strong>Single Identity:</strong> You agree to provide accurate, truthful name and
                academic profile details. Account sharing, credential distribution, or impersonation
                of other students or faculty members is strictly prohibited.
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>3. Peer-to-Peer Marketplace & Safety Guidelines</h2>
            <p>
              RamaiahMart acts solely as a communication and discovery board for campus peers. We
              facilitate listings for items such as textbooks, drafters, calculators, electronics,
              bicycles, and room essentials.
            </p>
            <ul>
              <li>
                <strong>Zero Commission:</strong> RamaiahMart charges zero platform fees or
                transaction commissions.
              </li>
              <li>
                <strong>In-Person Handoffs:</strong> All purchases, sales, rentals, and loans are
                conducted directly between students in person. We recommend meeting during daylight
                hours at visible campus landmark locations (e.g., Apex Block, Campus Canteen,
                Library steps).
              </li>
              <li>
                <strong>Payments:</strong> RamaiahMart does not process payments or escrow funds.
                Payments (via UPI or cash) must occur only upon physical inspection and handoff of
                the item. <em>Never transfer money in advance.</em>
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>4. Prohibited Items & Conduct</h2>
            <p>Users must not post, list, or solicit any of the following on RamaiahMart:</p>
            <ul>
              <li>Academic dishonesty materials (exam question leaks, unauthorized test papers, graded assignment solutions).</li>
              <li>Illegal substances, narcotics, alcohol, tobacco, vape products, or prescription pharmaceuticals.</li>
              <li>Weapons, hazardous equipment, firecrackers, or dangerous chemicals.</li>
              <li>Stolen property, counterfeit goods, or software infringing intellectual property rights.</li>
              <li>Offensive, harassing, defamatory, sexually explicit, or discriminatory content.</li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>5. Content Moderation & Account Suspension</h2>
            <p>
              All marketplace posts are subject to automated and human campus review before or
              immediately after publication. RamaiahMart reserves the right to reject, remove, or edit
              any listing and suspend or terminate any user account that violates these Terms or
              endangers the campus community.
            </p>
            <div className="legal-review-callout">
              <span className="legal-review-tag">[REVIEW REQUIRED: retention period]</span>
              <p>
                Specific data retention windows for removed posts, moderation records, and deleted
                user profiles require final policy confirmation.
              </p>
            </div>
          </section>

          <section className="legal-section">
            <h2>6. Limitation of Liability</h2>
            <p>
              RamaiahMart is provided on an &ldquo;as is&rdquo; and &ldquo;as available&rdquo; basis
              without warranties of any kind. RamaiahMart, its creator, and student maintainers are
              not liable for the quality, safety, legality, or condition of items listed by users,
              nor for any disputes, financial losses, or physical harm arising from transactions
              between users.
            </p>
          </section>

          <section className="legal-section">
            <h2>7. Contact & Grievance Redressal</h2>
            <p>
              For questions regarding these Terms or to report a campus listing violation:
            </p>
            <ul>
              <li>
                Engineering & Project Maintainer:{" "}
                <a href="mailto:mohammedrazim880@gmail.com" className="cookie-link">
                  mohammedrazim880@gmail.com
                </a>
              </li>
              <li>
                Institutional Campus Liaison:{" "}
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
