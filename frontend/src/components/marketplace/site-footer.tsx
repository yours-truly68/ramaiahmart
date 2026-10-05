"use client";

import Link from "next/link";
import {
  ArrowUp,
  ArrowUpRight,
  Github,
  Linkedin,
  Mail,
  MapPin,
  MessageCircle,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { openCookiePreferencesModal } from "@/lib/cookie-consent";

export function SiteFooter() {
  const currentYear = new Date().getFullYear();

  const scrollToTop = () => {
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  return (
    <footer className="site-footer" role="contentinfo" aria-label="Site footer">
      {/* Top Campus Trust Ribbon */}
      <div className="footer-ribbon">
        <div className="rm-container footer-ribbon-inner">
          <div className="ribbon-status">
            <span className="live-dot" aria-hidden="true" />
            <span className="ribbon-status-text">
              <strong>MSRIT Campus Network</strong> · Active Student Exchange
            </span>
          </div>
          <div className="ribbon-trust">
            <ShieldCheck size={15} aria-hidden="true" className="trust-icon" />
            <span>Verified @msrit.edu student access only · Zero commissions</span>
          </div>
          <button
            type="button"
            onClick={scrollToTop}
            className="back-to-top"
            aria-label="Back to top of page"
          >
            <span>Top</span>
            <ArrowUp size={14} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Main Multi-Column Body */}
      <div className="site-footer-inner rm-container">
        {/* Brand & Editorial Col */}
        <div className="footer-col footer-col-brand">
          <Link className="wordmark" href="/" aria-label="RamaiahMart home">
            Ramaiah<span>Mart</span>
          </Link>
          <p className="footer-tagline">
            The hyper-local peer exchange for students & faculty of Ramaiah Institute of Technology.
          </p>
          <div className="footer-location-badge">
            <MapPin size={14} aria-hidden="true" className="loc-icon" />
            <span>MSRIT Campus, Mathikere, Bengaluru 560054</span>
          </div>
          <p className="footer-handshake-note">
            Buy, sell, and borrow within your own campus. Safe hand-to-hand transactions at designated spots.
          </p>
        </div>

        {/* Navigation Col */}
        <div className="footer-col">
          <h3 className="footer-col-title">Marketplace</h3>
          <nav aria-label="Marketplace quick links" className="footer-link-list">
            <Link href="/#recent">Latest Campus Listings</Link>
            <Link href="/#categories">Browse by Category</Link>
            <Link href="/post/create?type=OFFER">Sell or Rent an Item</Link>
            <Link href="/post/create?type=REQUEST">Request What You Need</Link>
            <Link href="/#how-it-works">How Campus Exchange Works</Link>
          </nav>
        </div>

        {/* Safety & Guidelines Col */}
        <div className="footer-col">
          <h3 className="footer-col-title">Campus Guidelines</h3>
          <ul className="footer-guidelines-list">
            <li>
              <span className="guideline-check" aria-hidden="true">✓</span>
              <span>Meet at visible spots (Apex Block, Canteen, Library steps)</span>
            </li>
            <li>
              <span className="guideline-check" aria-hidden="true">✓</span>
              <span>Inspect items thoroughly before handing over payment</span>
            </li>
            <li>
              <span className="guideline-check" aria-hidden="true">✓</span>
              <span>UPI or cash on hand-off — never pay in advance</span>
            </li>
            <li>
              <span className="guideline-check" aria-hidden="true">✓</span>
              <span>All posts are reviewed by campus moderators</span>
            </li>
          </ul>
        </div>

        {/* Creator / Engineering Identity Col */}
        <div className="footer-col footer-col-identity">
          <div className="identity-header">
            <span className="identity-kicker">Created & Engineered By</span>
            <h4 className="identity-name">Mohammad Razim</h4>
            <p className="identity-meta">
              Alumni, Mechanical Engineering
              <br />
              Ramaiah Institute of Technology (MSRIT)
            </p>
          </div>

          <nav className="footer-social-grid" aria-label="Connect with Mohammad Razim">
            <a
              href="https://www.linkedin.com/in/mohammadrazim880"
              target="_blank"
              rel="noopener noreferrer"
              className="social-pill"
            >
              <Linkedin size={14} aria-hidden="true" />
              <span>LinkedIn</span>
              <ArrowUpRight size={13} aria-hidden="true" />
            </a>
            <a
              href="https://github.com/yours-truly68"
              target="_blank"
              rel="noopener noreferrer"
              className="social-pill"
            >
              <Github size={14} aria-hidden="true" />
              <span>GitHub</span>
              <ArrowUpRight size={13} aria-hidden="true" />
            </a>
            <a
              href="mailto:mohammedrazim880@gmail.com"
              className="social-pill"
            >
              <Mail size={14} aria-hidden="true" />
              <span>Email</span>
              <ArrowUpRight size={13} aria-hidden="true" />
            </a>
            <a
              href="https://wa.me/918867018007"
              target="_blank"
              rel="noopener noreferrer"
              className="social-pill"
            >
              <MessageCircle size={14} aria-hidden="true" />
              <span>WhatsApp</span>
              <ArrowUpRight size={13} aria-hidden="true" />
            </a>
          </nav>
        </div>
      </div>

      {/* Bottom Legal / Colophon */}
      <div className="footer-bottom">
        <div className="rm-container footer-bottom-inner">
          <p className="footer-copyright">
            © {currentYear} RamaiahMart · Developed for Ramaiah Institute of Technology students.
          </p>

          <nav className="footer-legal-row" aria-label="Legal and privacy links">
            <Link href="/terms" className="cookie-link">
              Terms &amp; Conditions
            </Link>
            <span aria-hidden="true">·</span>
            <Link href="/privacy" className="cookie-link">
              Privacy Policy
            </Link>
            <span aria-hidden="true">·</span>
            <button
              type="button"
              className="footer-legal-btn"
              onClick={openCookiePreferencesModal}
            >
              Cookie Preferences
            </button>
          </nav>

          <div className="footer-badges">
            <span className="badge-item">
              <Sparkles size={12} aria-hidden="true" />
              <span>Zero Commission</span>
            </span>
            <span className="badge-item">Peer-to-Peer</span>
            <span className="badge-item">Open Campus Initiative</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
