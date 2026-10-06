"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface LoginTransitionProps {
  destination: string;
  email?: string;
}

export function LoginTransition({ destination, email }: LoginTransitionProps) {
  const router = useRouter();
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    // Prefetch destination immediately so navigation is instant
    router.prefetch(destination);

    // Check if user prefers reduced motion
    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const exitDelay = prefersReducedMotion ? 400 : 1300;
    const redirectDelay = prefersReducedMotion ? 550 : 1600;

    const exitTimer = setTimeout(() => {
      setExiting(true);
    }, exitDelay);

    const redirectTimer = setTimeout(() => {
      router.replace(destination);
    }, redirectDelay);

    return () => {
      clearTimeout(exitTimer);
      clearTimeout(redirectTimer);
    };
  }, [destination, router]);

  const username = email ? email.split("@")[0] : null;

  return (
    <div
      className={`login-transition-overlay ${exiting ? "login-transition--exiting" : ""}`}
      role="status"
      aria-live="polite"
      aria-label="Logging you in to RamaiahMart…"
    >
      <div className="login-transition-ambient" aria-hidden="true" />
      <div className="login-transition-content">
        <div className="login-transition-logo-wrap">
          <div className="login-transition-halo" aria-hidden="true" />
          <div className="login-transition-icon">
            <Image
              src="/icon.png"
              alt="RamaiahMart Logo"
              width={76}
              height={76}
              priority
              className="login-transition-logo-img"
            />
          </div>
        </div>

        <div className="login-transition-wordmark">
          Ramaiah<span>Mart</span>
        </div>

        <p className="login-transition-greeting">
          {username ? `Welcome back, ${username}` : "Welcome back to campus"}
        </p>

        <div className="login-transition-progress-wrap" aria-hidden="true">
          <div className="login-transition-progress-bar" />
        </div>

        <div className="login-transition-status">
          <span className="login-transition-dot" aria-hidden="true" />
          <span>Opening your marketplace…</span>
        </div>
      </div>
    </div>
  );
}
