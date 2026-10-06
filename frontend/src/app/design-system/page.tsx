import { ArrowDown, ArrowUpRight, Check, PackageOpen } from "lucide-react";
import Link from "next/link";
import { Avatar, Badge, Card, Divider, EmptyState, SectionHeading, Skeleton, StatusBadge, type PostStatus } from "@/components/ui";
import { ControlSpecimens } from "./specimens";
import "./specimen.css";

const palette = [
  ["background", "Cream", "#FAF6EE"], ["foreground", "Ink", "#171714"],
  ["muted-foreground", "Muted ink", "#666159"], ["border", "Fine line", "#E4DED4"],
  ["card", "Paper", "#FFFDF9"], ["accent-orange", "Campus orange", "#FF5A1F"],
  ["accent-soft-orange", "Soft orange", "#FFE5D3"], ["success", "Success", "#246039"],
  ["warning", "Warning", "#805100"], ["destructive", "Destructive", "#A72F2B"],
  ["offer", "Offer", "#98380F"], ["request", "Request", "#274F8E"],
];
const states: PostStatus[] = ["DRAFT", "PENDING_REVIEW", "PUBLISHED", "REJECTED", "ARCHIVED", "SOLD", "RENTED", "CLOSED"];

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Design System",
  robots: {
    index: false,
    follow: false,
  },
};

export default function DesignSystem() {
  return (
    <>
      <header className="spec-header rm-container">
        <Link href="/" className="spec-wordmark" aria-label="RamaiahMart home">Ramaiah<span>Mart</span></Link>
        <span className="rm-meta rm-muted">Design system / 1.0</span>
        <nav aria-label="Design system"><a href="#foundations">Foundations</a><a href="#components">Components</a><a href="#states">States</a></nav>
      </header>
      <main id="main" className="rm-container">
        <section className="spec-intro" aria-labelledby="intro-title">
          <div>
            <h1 id="intro-title" className="rm-display">Same campus.<br />Shared language.</h1>
            <p className="rm-lead rm-muted">A warm, considered foundation for RamaiahMart.<br className="spec-desktop-break" /> Made for the things we have. And the things we need.</p>
            <a className="spec-jump" href="#components">Explore the components <ArrowDown size={18} aria-hidden="true" /></a>
          </div>
          <div className="spec-type-poster" aria-label="Satoshi typeface specimen">
            <span className="spec-aa" aria-hidden="true">Aa<span>.</span></span>
            <div className="spec-poster-footer"><strong>Satoshi</strong><span className="rm-meta">Bold by nature.<br />Room to breathe.</span></div>
          </div>
        </section>
        <div className="spec-purpose"><span className="rm-meta">A component specimen, with illustrative content.</span><span className="rm-meta rm-muted">Warm surfaces. Clear actions. A little campus character.</span></div>
        <section id="foundations" className="spec-section" aria-labelledby="foundations-title">
          <SectionHeading title="A little colour. A lot of clarity." description="Cream is the canvas. Ink does the talking. Orange earns its place." />
          <h2 id="foundations-title" className="sr-only">Colour foundations</h2>
          <div className="spec-palette">{palette.map(([token, name, value]) => <div key={token} className="spec-colour"><div className="spec-swatch" style={{ background: `var(--${token})` }} /><strong>{name}</strong><span className="rm-meta rm-muted">{value}</span><code>{token}</code></div>)}</div>
          <div className="spec-type-scale">
            <div><h3 className="rm-heading-sm">Type with room to speak.</h3><p className="rm-muted">Satoshi for the big moments.<br />Inter or system sans for the everyday.</p></div>
            <div className="spec-type-samples"><div><span className="rm-meta rm-muted">Display · 48–96</span><p className="rm-display">Already on campus.</p></div><Divider /><div><span className="rm-meta rm-muted">Heading · 28–40</span><p className="rm-heading">Good things, closer.</p></div><Divider /><div><span className="rm-meta rm-muted">Body · 16</span><p>Buy. Sell. Rent. Borrow. Find services. Post what you need.</p></div><div><span className="rm-meta rm-muted">Metadata · 13</span><p className="rm-meta">Campus location · A moment ago</p></div></div>
          </div>
        </section>
        <section id="components" className="spec-section" aria-labelledby="components-title">
          <h2 id="components-title" className="rm-heading">Small parts. One familiar feeling.</h2>
          <p className="rm-muted spec-section-description">Everyday controls with clear labels, comfortable targets, and visible focus.</p>
          <ControlSpecimens />
          <div className="spec-component-row"><div><h3 className="rm-heading-sm">Surfaces</h3><p className="rm-meta rm-muted">12px corners / fine borders<br />Soft elevation only when needed.</p></div><div className="spec-surfaces"><Card><span className="rm-meta rm-muted">Default</span><h4>Room for what matters.</h4><p className="rm-meta rm-muted">A quiet surface for related content.</p></Card><Card surface="sage"><span className="rm-meta">Sage</span><h4>A softer supporting role.</h4><p className="rm-meta">Pastels group and guide.</p></Card><Card surface="orange" elevated><span className="rm-meta">Soft orange / elevated</span><h4>A little emphasis.</h4><p className="rm-meta">Warmth without extra chrome.</p></Card></div></div>
          <div className="spec-component-row"><div><h3 className="rm-heading-sm">Identity & labels</h3><p className="rm-meta rm-muted">Names and words carry meaning.<br />Colour supports them.</p></div><div className="spec-stack"><div className="spec-row"><Avatar name="Ramaiah Student" size="lg" /><Avatar name="Ramaiah Student" /><Avatar name="Ramaiah Student" size="sm" /><span className="rm-meta rm-muted">Initials fallback · illustrative identity</span></div><div className="spec-row"><Badge tone="offer">Offer</Badge><Badge tone="request">Request</Badge><Badge tone="success"><Check size={14} aria-hidden="true" />Verified student</Badge><Badge>Neutral</Badge></div></div></div>
        </section>
        <section id="states" className="spec-section" aria-labelledby="states-title">
          <h2 id="states-title" className="rm-heading">Clear, even between moments.</h2>
          <p className="rm-muted spec-section-description">Status, absence, and loading belong to the same visual language.</p>
          <div className="spec-row spec-status-row">{states.map(status => <StatusBadge status={status} key={status} />)}</div>
          <div className="spec-state-grid"><Card><EmptyState icon={<PackageOpen size={32} strokeWidth={1.5} />} title="Nothing here yet." description="When there’s something to show, it will appear here." /><p className="rm-meta rm-muted spec-caption">EmptyState · a useful explanation, without unnecessary decoration.</p></Card><Card><div role="status" aria-label="Loading specimen" aria-busy="true" className="spec-loading"><Skeleton shape="circle" /><div className="spec-stack"><Skeleton /><Skeleton style={{ width: "65%" }} /></div><Skeleton shape="image" /><Skeleton style={{ width: "75%" }} /><Skeleton style={{ width: "45%" }} /></div><p className="rm-meta rm-muted spec-caption">Skeleton · geometry stays steady while content arrives.</p></Card></div>
        </section>
        <footer className="spec-footer"><span className="spec-wordmark">Ramaiah<span>Mart</span></span><p className="rm-meta rm-muted">Built from the approved campus references.<br />Ready to carry the next page.</p><a href="#main" className="spec-jump">Back to top <ArrowUpRight size={18} aria-hidden="true" /></a></footer>
      </main>
    </>
  );
}
