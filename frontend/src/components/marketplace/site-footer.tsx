"use client";

import Link from "next/link";
import {
  ArrowUp,
  ArrowUpRight,
  Github,
  GraduationCap,
  Linkedin,
  Mail,
  MapPin,
  MessageCircle,
  ShieldCheck,
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
    <footer className="site-footer" role="contentinfo" aria-label="RamaiahMart site footer">
      {/* Top Campus Orientation Bar */}
      <div className="footer-ribbon">
        <div className="rm-container footer-ribbon-inner">
          <div className="ribbon-identity">
            <span className="ribbon-tag">MSRIT Campus Network</span>
            <span className="ribbon-divider" aria-hidden="true">/</span>
            <span className="ribbon-text">Autonomous Student Peer Exchange</span>
          </div>
          <div className="ribbon-actions">
            <span className="ribbon-verification">
              <ShieldCheck size={14} aria-hidden="true" className="ribbon-icon" />
              <span>@msrit.edu verified community</span>
            </span>
            <button
              type="button"
              onClick={scrollToTop}
              className="back-to-top"
              aria-label="Back to top of page"
            >
              <span>Back to top</span>
              <ArrowUp size={13} aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      {/* Main 4-Column Editorial Body */}
      <div className="site-footer-inner rm-container">
        {/* Col 1: Brand & Purpose */}
        <div className="footer-col footer-col-brand">
          <Link className="wordmark" href="/" aria-label="RamaiahMart home">
            Ramaiah<span>Mart</span>
          </Link>
          <p className="footer-tagline">
            The hyper-local peer exchange for Ramaiah Institute of Technology. Circulating textbooks, calculators, electronics, lab tools, and hostel essentials directly between students.
          </p>
          <div className="footer-campus-card">
            <MapPin size={14} aria-hidden="true" className="campus-pin-icon" />
            <div className="campus-meta">
              <span className="campus-name">Ramaiah Institute of Technology</span>
              <span className="campus-address">M S Ramaiah Nagar, Mathikere, Bengaluru 560054</span>
            </div>
          </div>
        </div>

        {/* Col 2: Marketplace Navigation */}
        <div className="footer-col">
          <h3 className="footer-col-title">Marketplace</h3>
          <nav aria-label="Marketplace directory" className="footer-link-list">
            <Link href="/#recent">Latest campus listings</Link>
            <Link href="/#categories">Browse by category</Link>
            <Link href="/post/create?type=OFFER">List an item (Sell / Rent)</Link>
            <Link href="/post/create?type=REQUEST">Request what you need</Link>
            <Link href="/#how-it-works">How campus hand-off works</Link>
          </nav>
        </div>

        {/* Col 3: Safe Exchange Field Guide */}
        <div className="footer-col footer-col-safety">
          <h3 className="footer-col-title">Campus Hand-off Protocol</h3>
          <dl className="footer-safety-guide">
            <div className="safety-item">
              <dt className="safety-dt">Designated spots</dt>
              <dd className="safety-dd">Meet at Apex Block foyer, Central Library portico, or Freshers Canteen.</dd>
            </div>
            <div className="safety-item">
              <dt className="safety-dt">Physical inspection</dt>
              <dd className="safety-dd">Check calculator functions, lab kits, or book editions before payment.</dd>
            </div>
            <div className="safety-item">
              <dt className="safety-dt">Payment on delivery</dt>
              <dd className="safety-dd">Pay via UPI or cash upon physical exchange. Never transfer advance deposits.</dd>
            </div>
            <div className="safety-item">
              <dt className="safety-dt">Student verified</dt>
              <dd className="safety-dd">All listings authenticated via institutional email with zero platform commission.</dd>
            </div>
          </dl>
        </div>

        {/* Col 4: Human Colophon & Creator Details */}
        <div className="footer-col footer-col-colophon">
          <h3 className="footer-col-title">Project Colophon</h3>
          <div className="colophon-card">
            <div className="colophon-author">
              <GraduationCap size={16} aria-hidden="true" className="colophon-icon" />
              <div>
                <span className="author-name">Mohammad Razim</span>
                <span className="author-title">Mechanical Engineering · MSRIT Alumni</span>
              </div>
            </div>
            <p className="colophon-note">
              Designed and engineered to give Ramaiah students an honest, zero-fee way to pass down campus essentials and keep useful gear circulating locally.
            </p>
            <div className="colophon-links" aria-label="Connect with Mohammad Razim">
              <a
                href="https://github.com/yours-truly68"
                target="_blank"
                rel="noopener noreferrer"
                className="colophon-link"
                title="GitHub profile"
              >
                <Github size={13} aria-hidden="true" />
                <span>GitHub</span>
                <ArrowUpRight size={11} aria-hidden="true" className="link-arrow" />
              </a>
              <a
                href="https://www.linkedin.com/in/mohammadrazim880"
                target="_blank"
                rel="noopener noreferrer"
                className="colophon-link"
                title="LinkedIn profile"
              >
                <Linkedin size={13} aria-hidden="true" />
                <span>LinkedIn</span>
                <ArrowUpRight size={11} aria-hidden="true" className="link-arrow" />
              </a>
              <a
                href="mailto:mohammedrazim880@gmail.com"
                className="colophon-link"
                title="Email direct"
              >
                <Mail size={13} aria-hidden="true" />
                <span>Email</span>
                <ArrowUpRight size={11} aria-hidden="true" className="link-arrow" />
              </a>
              <a
                href="https://wa.me/918867018007"
                target="_blank"
                rel="noopener noreferrer"
                className="colophon-link"
                title="WhatsApp message"
              >
                <MessageCircle size={13} aria-hidden="true" />
                <span>WhatsApp</span>
                <ArrowUpRight size={11} aria-hidden="true" className="link-arrow" />
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Legal & Colophon Bar */}
      <div className="footer-bottom">
        <div className="rm-container footer-bottom-inner">
          <p className="footer-copyright">
            © {currentYear} RamaiahMart. An independent student initiative for Ramaiah Institute of Technology.
          </p>

          <nav className="footer-legal-row" aria-label="Legal documents and privacy consent">
            <Link href="/terms" className="cookie-link">
              Terms of Service
            </Link>
            <span className="legal-dot" aria-hidden="true">·</span>
            <Link href="/privacy" className="cookie-link">
              Privacy Policy
            </Link>
            <span className="legal-dot" aria-hidden="true">·</span>
            <button
              type="button"
              className="footer-legal-btn"
              onClick={openCookiePreferencesModal}
            >
              Cookie Preferences
            </button>
          </nav>

          <div className="footer-ethos">
            <span>Direct P2P</span>
            <span className="ethos-dot" aria-hidden="true">/</span>
            <span>Zero Fees</span>
            <span className="ethos-dot" aria-hidden="true">/</span>
            <span>Campus First</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
