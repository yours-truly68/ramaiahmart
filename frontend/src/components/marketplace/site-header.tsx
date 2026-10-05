"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowUpRight, Search } from "lucide-react";
import { useSession } from "@/lib/auth/session";
import { Avatar } from "@/components/ui";
export function SiteHeader({ auth }: { auth?: "login" | "register" }) {
  const session = useSession();
  const pathname = usePathname();
  const isBrowse = pathname === "/";
  return <header className="market-header"><div className="market-header-inner rm-container">
    <Link href="/" className="wordmark" aria-label="RamaiahMart home">Ramaiah<span>Mart</span></Link>
    <nav aria-label="Main navigation"><Link href="/#recent" className={isBrowse ? "nav-active" : undefined}>Browse</Link><Link href="/#categories">Categories</Link><Link href="/#how-it-works">How it works</Link></nav>
    <div className="header-actions">
      {auth ? <><span className="auth-header-note">{auth === "login" ? "New to campus exchange?" : "Already one of us?"}</span><Link className="auth-header-link" href={auth === "login" ? "/register" : "/login"}>{auth === "login" ? "Sign up" : "Log in"}<ArrowUpRight size={16} /></Link></> : <>
        <Link href="/#market-search" className="header-search text-action" aria-label="Search marketplace"><Search size={20} /><span>Search</span></Link>
        {session.data ? <Link href="/profile" className="profile-link" aria-label="Your profile"><Avatar name={session.data.name} size="sm" /></Link> : <Link href="/login" className="text-action">Log in</Link>}
        <Link href="/post/create" className="rm-button rm-button--primary rm-button--md header-post">Post Item<span className="orange-arrow"><ArrowUpRight size={14} /></span></Link>
      </>}
    </div>
  </div></header>;
}
export function SiteFooter() {
  return <footer className="site-footer"><div className="site-footer-inner rm-container">
    <div className="footer-brand"><Link className="wordmark" href="/" aria-label="RamaiahMart home">Ramaiah<span>Mart</span></Link><p>Students. Stuff. Same campus.</p></div>
    <div className="footer-identity"><h2>Mohammad Razim</h2><p>Alumni, Mechanical Engineering</p><p>Ramaiah Institute of Technology</p></div>
    <nav className="footer-contact" aria-label="Mohammad Razim’s social and contact links">
      <a href="https://www.linkedin.com/in/mohammadrazim880" target="_blank" rel="noopener noreferrer">LinkedIn<ArrowUpRight size={16} aria-hidden="true" /></a>
      <a href="https://www.github.com/yours-truly68" target="_blank" rel="noopener noreferrer">GitHub<ArrowUpRight size={16} aria-hidden="true" /></a>
      <a href="mailto:mohammedrazim880@gmail.com">mohammedrazim880@gmail.com<ArrowUpRight size={16} aria-hidden="true" /></a>
      <a href="https://wa.me/918867018007" target="_blank" rel="noopener noreferrer">WhatsApp · +91 8867018007<ArrowUpRight size={16} aria-hidden="true" /></a>
    </nav>
  </div></footer>;
}
