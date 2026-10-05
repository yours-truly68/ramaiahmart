"use client";

import { useState, type KeyboardEvent } from "react";
import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, ArrowRight, BookOpen, Camera, Check, Clock3, Laptop, Search, ShieldCheck } from "lucide-react";

const steps = [
  { label: "Explore", title: "Find your kind of thing.", copy: "Browse offers or see what fellow students need.", action: "Browse the feed", href: "/#recent" },
  { label: "Post", title: "Make your first post.", copy: "Add the details, a photo, and your price or budget.", action: "Create a post", href: "/post/create" },
  { label: "Review", title: "One last look. Then campus.", copy: "Preview your post and submit. Track its moderation status in your profile.", action: "View your profile", href: "/profile" },
];

function DemoScene({ step }: { step: number }) {
  return <div className={`walkthrough-scene scene-${step}`} aria-hidden="true">
    <div className="demo-window">
      <div className="demo-window-bar"><span className="demo-brand">Ramaiah<span>Mart</span></span><span className="demo-label">Demo preview</span></div>
      {step === 0 ? <div className="demo-browse">
        <div className="demo-search"><Search size={17} />Search campus…</div>
        <div className="demo-switch"><span>Offers</span><span>Requests</span></div>
        <div className="demo-categories"><span><Laptop size={24} />Electronics</span><span><BookOpen size={24} />Books</span></div>
        <div className="demo-feed-lines"><span /><span /><span /></div>
      </div> : step === 1 ? <div className="demo-compose">
        <div className="demo-photo"><Image src="/images/campus-room.png" alt="" fill sizes="(max-width: 640px) 70vw, 260px" /><span><Camera size={15} />Add your photos</span></div>
        <div className="demo-fields"><span className="demo-field-title">The details</span><span>Title<i /></span><span>Category<i /></span><span>Price / budget<i /></span></div>
      </div> : <div className="demo-review">
        <div className="demo-review-icon"><ShieldCheck size={36} strokeWidth={1.5} /></div>
        <strong>Ready for campus?</strong>
        <div className="demo-checks"><span><Check size={15} />Details added</span><span><Check size={15} />Preview checked</span></div>
        <div className="demo-status"><Clock3 size={17} />Pending review</div>
        <span className="demo-status-note">Published after approval</span>
      </div>}
    </div>
    <span className="demo-sticker">{step === 0 ? "Your campus, closer." : step === 1 ? "A little less clutter." : "You’re in the loop."}</span>
  </div>;
}

export function HowItWorks() {
  const [active, setActive] = useState(0);
  function selectFromKeyboard(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const next = event.key === "ArrowRight" ? (index + 1) % steps.length : event.key === "ArrowLeft" ? (index + steps.length - 1) % steps.length : event.key === "Home" ? 0 : event.key === "End" ? steps.length - 1 : null;
    if (next === null) return;
    event.preventDefault(); setActive(next); document.getElementById(`walkthrough-tab-${next}`)?.focus();
  }
  return <section id="how-it-works" className="walkthrough rm-container" aria-labelledby="walkthrough-heading">
    <div className="walkthrough-heading"><h2 id="walkthrough-heading">A quick look around.</h2><span>How it works</span></div>
    <div className="walkthrough-body">
      <div className="walkthrough-content">
        <div className="walkthrough-tabs" role="tablist" aria-label="Marketplace walkthrough">{steps.map((item, index) => <button key={item.label} id={`walkthrough-tab-${index}`} role="tab" aria-selected={active === index} aria-controls={`walkthrough-panel-${index}`} tabIndex={active === index ? 0 : -1} onClick={() => setActive(index)} onKeyDown={event => selectFromKeyboard(event, index)}><span>0{index + 1}</span>{item.label}</button>)}</div>
        <div className="walkthrough-panels">{steps.map((item, index) => <div key={item.label} id={`walkthrough-panel-${index}`} className={`walkthrough-panel ${active === index ? "is-active" : ""}`} role="tabpanel" aria-labelledby={`walkthrough-tab-${index}`} aria-hidden={active !== index} inert={active !== index} tabIndex={active === index ? 0 : -1}><div className="walkthrough-panel-copy"><h3>{item.title}</h3><p>{item.copy}</p><Link className="text-action" href={item.href}>{item.action}<ArrowRight size={17} /></Link></div></div>)}</div>
        <div className="walkthrough-navigation"><span aria-live="polite">{active + 1} / {steps.length}</span><div><button aria-label="Previous step" disabled={active === 0} onClick={() => setActive(active - 1)}><ArrowLeft size={19} /></button><button aria-label="Next step" disabled={active === steps.length - 1} onClick={() => setActive(active + 1)}><ArrowRight size={19} /></button></div></div>
      </div>
      <div className="walkthrough-scenes">{steps.map((item, index) => <div key={item.label} className={`walkthrough-scene-slot ${active === index ? "is-active" : ""}`}><DemoScene step={index} /></div>)}</div>
    </div>
  </section>;
}
