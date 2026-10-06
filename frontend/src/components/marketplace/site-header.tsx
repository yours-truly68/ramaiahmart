"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, MessageSquare, Search } from "lucide-react";
import { api } from "@/lib/api/client";
import { useSession } from "@/lib/auth/session";
import type { ConversationListResponse } from "@/lib/api/types";
import { Avatar } from "@/components/ui";

export function SiteHeader({ auth }: { auth?: "login" | "register" }) {
  const session = useSession();
  const pathname = usePathname();
  const isBrowse = pathname === "/";

  const conversationsQuery = useQuery({
    queryKey: ["conversations"],
    queryFn: ({ signal }) => api<ConversationListResponse>("conversations", { signal }),
    enabled: !!session.data,
    refetchInterval: 15000,
  });
  const unreadCount = conversationsQuery.data?.unread_total ?? 0;

  const handleNavScroll = (event: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (pathname === "/" && href.startsWith("/#")) {
      const id = href.replace("/#", "");
      const element = document.getElementById(id);
      if (element) {
        event.preventDefault();
        const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        element.scrollIntoView({
          behavior: prefersReducedMotion ? "auto" : "smooth",
          block: "start",
        });
        window.history.pushState(null, "", href);
      }
    }
  };

  return <header className="market-header"><div className="market-header-inner rm-container">
    <Link href="/" className="wordmark" aria-label="RamaiahMart home">Ramaiah<span>Mart</span></Link>
    <nav aria-label="Main navigation">
      <Link href="/#recent" className={isBrowse ? "nav-active" : undefined} onClick={e => handleNavScroll(e, "/#recent")}>Browse</Link>
      <Link href="/#categories" onClick={e => handleNavScroll(e, "/#categories")}>Categories</Link>
      <Link href="/#how-it-works" onClick={e => handleNavScroll(e, "/#how-it-works")}>How it works</Link>
    </nav>
    <div className="header-actions">
      {auth ? <><span className="auth-header-note">{auth === "login" ? "New to campus exchange?" : "Already one of us?"}</span><Link className="auth-header-link" href={auth === "login" ? "/register" : "/login"}>{auth === "login" ? "Sign up" : "Log in"}<ArrowUpRight size={16} /></Link></> : <>
        <Link href="/#market-search" className="header-search text-action" aria-label="Search marketplace" onClick={e => handleNavScroll(e, "/#market-search")}><Search size={20} /><span>Search</span></Link>
        {session.data ? (
          <>
            <Link
              href="/messages"
              className="header-messages text-action"
              aria-label={unreadCount > 0 ? `Messages (${unreadCount} unread)` : "Messages"}
              style={{ position: "relative", display: "inline-flex", alignItems: "center", justifyContent: "center", width: "36px", height: "36px" }}
            >
              <MessageSquare size={19} />
              {unreadCount > 0 && (
                <span
                  style={{
                    position: "absolute",
                    top: "2px",
                    right: "2px",
                    background: "var(--accent-orange)",
                    color: "#ffffff",
                    fontSize: "10px",
                    fontWeight: 700,
                    borderRadius: "999px",
                    minWidth: "16px",
                    height: "16px",
                    padding: "0 4px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    lineHeight: 1,
                  }}
                >
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </Link>
            <Link href="/profile" className="profile-link" aria-label="Your profile"><Avatar name={session.data.name} size="sm" /></Link>
          </>
        ) : (
          <Link href="/login" className="text-action">Log in</Link>
        )}
        <Link href="/post/create" className="rm-button rm-button--primary rm-button--md header-post">Post Item<span className="orange-arrow"><ArrowUpRight size={14} /></span></Link>
      </>}
    </div>
  </div></header>;
}
export { SiteFooter } from "./site-footer";
