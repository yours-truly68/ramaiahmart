import type { Metadata } from "next";
import Link from "next/link";
import { FileText } from "lucide-react";
import { SiteHeader } from "@/components/marketplace/site-header";
import { SiteFooter } from "@/components/marketplace/site-footer";

export const metadata: Metadata = {
  title: "Terms & Conditions",
  description:
    "Terms of Service governing student access, marketplace exchange rules, account lifecycle, peer transactions, and conduct on RamaiahMart.",
  alternates: {
    canonical: "/terms",
  },
  openGraph: {
    title: "Terms & Conditions — RamaiahMart",
    description:
      "Platform agreement and Terms of Service governing student access on RamaiahMart.",
    url: "/terms",
  },
  robots: {
    index: true,
    follow: true,
  },
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
            <h2>1. Introduction & Institutional Non-Affiliation</h2>
            <p>
              Welcome to <strong>RamaiahMart</strong>. RamaiahMart is an open,
              hyper-local peer-to-peer exchange platform created for the student
              community of Ramaiah Institute of Technology (MSRIT), Bengaluru.
            </p>
            <p>
              <strong>Institutional Non-Affiliation:</strong> RamaiahMart is an
              independent student project operated by{" "}
              <strong>Mohammad Razim</strong>. RamaiahMart is{" "}
              <strong>
                not affiliated with, owned by, operated by, sponsored by, or
                endorsed by Ramaiah Institute of Technology (MSRIT/RIT)
              </strong>
              .
            </p>
            <p>
              By accessing RamaiahMart or registering an account, you agree to
              comply with and be bound by these Terms & Conditions and our{" "}
              <Link href="/privacy" className="cookie-link">
                Privacy Policy
              </Link>
              . If you do not agree to these terms, you may not create an
              account or publish listings on the platform.
            </p>
          </section>

          <section className="legal-section">
            <h2>2. Account Eligibility & Responsibilities</h2>
            <ul>
              <li>
                <strong>Eligible Users:</strong> Account registration is
                intended for students and members of the campus community
                possessing an authorized university email address (such as{" "}
                <code>@msrit.edu</code>).
              </li>
              <li>
                <strong>Account Security:</strong> You are responsible for
                safeguarding your login credentials. You must promptly report
                any unauthorized use of your account to{" "}
                <a
                  href="mailto:mohammedrazim880@gmail.com"
                  className="cookie-link"
                >
                  mohammedrazim880@gmail.com
                </a>
                .
              </li>
              <li>
                <strong>Truthful Information:</strong> You agree to provide
                accurate name and academic profile details. Account sharing,
                credential trading, or impersonating other students, staff, or
                faculty is strictly prohibited.
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>3. Peer-to-Peer Marketplace & Platform Role</h2>
            <p>
              RamaiahMart acts solely as an informational board and discovery
              platform for campus peers to connect and communicate.
            </p>
            <ul>
              <li>
                <strong>Not a Transaction Party:</strong> RamaiahMart is not a
                buyer, seller, lender, renter, tenant, tutor, service provider,
                or broker in any user exchange. All transactions, negotiations,
                and handoffs are strictly between the involved users.
              </li>
              <li>
                <strong>Zero Commissions:</strong> RamaiahMart charges zero
                fees, takes zero commissions, and does not process payments or
                hold escrow funds.
              </li>
              <li>
                <strong>Evaluation Responsibility:</strong> Users are solely
                responsible for inspecting items, verifying their functionality
                and authenticity, and agreeing on terms before completing an
                exchange.
              </li>
              <li>
                <strong>Safe In-Person Handoffs:</strong> We strongly encourage
                meeting in well-lit, public campus locations during regular
                hours (e.g., Campus Canteen,Quadrangle, DES Stairs, ESB, Apex
                Block, Library steps).{" "}
                <em>Never send advance payments online.</em>
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>4. Listing Requirements & Prohibited Content</h2>
            <p>
              All listings must reflect genuine campus items and requests. Users
              may not post, solicit, or share:
            </p>
            <ul>
              <li>
                Academic dishonesty materials (exam papers, test leaks, graded
                assignment solutions).
              </li>
              <li>
                Narcotics, illegal substances, alcohol, tobacco, e-cigarettes,
                or prescription medications.
              </li>
              <li>
                Weapons, explosives, hazardous chemicals, or dangerous items.
              </li>
              <li>
                Stolen goods, counterfeit items, or content infringing
                third-party intellectual property rights.
              </li>
              <li>
                Harassing, defamatory, abusive, sexually explicit, fraudulent,
                or discriminatory content.
              </li>
              <li>
                Automated spam, commercial advertising, or links to external
                phishing sites.
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>5. Moderation, Reports & Account Suspension</h2>
            <p>
              To maintain campus safety, RamaiahMart reserves the right to
              review, edit, reject, or remove any listing at any time. Users can
              submit reports regarding suspicious or offensive posts. Accounts
              found violating these Terms or engaging in abusive behavior may be
              temporarily restricted or permanently suspended.
            </p>
          </section>

          <section className="legal-section">
            <h2>6. Account Lifecycle: Inactivity & Deletion</h2>
            <p>
              RamaiahMart respects user control over account status and data:
            </p>
            <ul>
              <li>
                <strong>Non-Destructive Inactivity:</strong> An account with no
                meaningful activity for approximately 90 days may be marked{" "}
                <code>INACTIVE</code>. Inactivity carries no penalty, no
                suspension, no loss of posts, and no loss of access. Performing
                any authenticated activity restores the account to{" "}
                <code>ACTIVE</code> status.
              </li>
              <li>
                <strong>User-Requested Deletion:</strong> You may request
                account deletion at any time via your profile settings.
                Submitting a deletion request places your account into a{" "}
                <strong>15-day grace period</strong> (
                <code>DELETION_PENDING</code>).
              </li>
              <li>
                <strong>Grace Period Cancellation:</strong> Logging in or
                performing authenticated activity during the 15-day grace period
                automatically cancels the deletion request. You may also click
                &ldquo;Cancel deletion&rdquo; in your profile.
              </li>
              <li>
                <strong>Permanent Deletion:</strong> If 15 days pass without
                cancellation or activity, the account, profile data, listings,
                media images, and messages are permanently purged from the
                active database and object storage.
              </li>
              <li>
                <strong>Disaster-Recovery Backups:</strong> Disaster recovery
                backups maintain a rolling 7-day retention schedule. Permanently
                deleted records are omitted from subsequent backup generations
                and rotate out of the archive.
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>7. Intellectual Property</h2>
            <p>
              You retain ownership of the photos, descriptions, and content you
              post on RamaiahMart. By posting on RamaiahMart, you grant the
              platform a non-exclusive, royalty-free, limited license to display
              your listing content to other campus users for the purpose of
              marketplace functionality.
            </p>
          </section>

          <section className="legal-section">
            <h2>8. Service Availability & Changes</h2>
            <p>
              RamaiahMart is provided as a student initiative. While we strive
              for high reliability and uptime, we do not guarantee uninterrupted
              or error-free operation. We reserve the right to update, modify,
              or discontinue features with reasonable notice to users.
            </p>
          </section>

          <section className="legal-section">
            <h2>9. Limitation of Liability</h2>
            <p>
              To the fullest extent permitted by applicable law, RamaiahMart and
              its operator are provided on an &ldquo;as is&rdquo; and &ldquo;as
              available&rdquo; basis. RamaiahMart is not liable for indirect,
              incidental, or consequential damages, nor for any financial
              disputes, lost opportunities, or physical injuries arising from
              user-to-user interactions, transactions, or listings posted on the
              service.
            </p>
          </section>

          <section className="legal-section">
            <h2>10. Contact Information</h2>
            <p>
              For legal inquiries, dispute reporting, platform questions, or
              privacy requests, contact:
            </p>
            <p>
              <strong>Mohammad Razim</strong>
              <br />
              Email:{" "}
              <a
                href="mailto:mohammedrazim880@gmail.com"
                className="cookie-link"
              >
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
