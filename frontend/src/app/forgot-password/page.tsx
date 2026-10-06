import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, ArrowRight, KeyRound, Mail } from "lucide-react";
import { SiteHeader } from "@/components/marketplace/site-header";
import { SiteFooter } from "@/components/marketplace/site-footer";

export const metadata: Metadata = {
  title: "Forgot password",
  description:
    "RamaiahMart account recovery: automated password-reset emails are currently unavailable. Contact RamaiahMart support with your @msrit.edu address.",
  alternates: {
    canonical: "/forgot-password",
  },
  openGraph: {
    title: "Forgot password — RamaiahMart",
    description:
      "RamaiahMart account recovery instructions for verified student accounts.",
    url: "/forgot-password",
  },
  robots: {
    index: true,
    follow: true,
  },
};


export default function ForgotPasswordPage() {
  return (
    <>
      <SiteHeader auth="login" />
      <main id="main" className="auth-page rm-container auth-page--login">
        <section className="auth-form-card" aria-labelledby="forgot-heading">
          <p className="eyebrow">Account recovery</p>
          <h2 id="forgot-heading" tabIndex={-1}>
            Forgot your password?
          </h2>
          <p className="auth-form-intro">
            Automated password reset is currently unavailable. RamaiahMart
            support will handle your recovery request manually.
          </p>
          <div className="panel-form recovery-card">
            <span className="recovery-mark" aria-hidden="true">
              <KeyRound size={24} />
            </span>
            <p>
              Please contact RamaiahMart support at{" "}
              <a href="mailto:mohammedrazim880@gmail.com" className="cookie-link">
                mohammedrazim880@gmail.com
              </a>
              .
            </p>
            <p>
              Include the <strong>@msrit.edu email address</strong> associated
              with your account, and mention that you would like help
              recovering access.
            </p>
            <a
              className="rm-button rm-button--accent rm-button--md"
              href="mailto:mohammedrazim880@gmail.com?subject=RamaiahMart%20password%20recovery%20request&body=My%20RamaiahMart%20account%20email%3A%20"
            >
              <Mail size={18} />
              Email support for recovery
            </a>
            <p className="recovery-fine-print">
              Recovery requests are reviewed manually. Contacting support does
              not guarantee that access can be restored.
            </p>
          </div>
          <p className="auth-switch">
            <Link href="/login">
              <ArrowLeft size={14} />
              Back to log in
            </Link>
          </p>
          <p className="auth-switch">
            New to RamaiahMart?{" "}
            <Link href="/register">
              Create an account
              <ArrowRight size={14} />
            </Link>
          </p>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
