"use client";

import { ArrowRight, Heart, Mail, Plus, X } from "lucide-react";
import { useState } from "react";
import { Button, IconButton, Input, SearchInput } from "@/components/ui";

export function ControlSpecimens() {
  const [pressed, setPressed] = useState(false);
  const [requiredValue, setRequiredValue] = useState("");
  const [notice, setNotice] = useState("Try an enabled button to inspect its feedback.");
  return <>
    <div className="spec-component-row"><div><h3 className="rm-heading-sm">Buttons</h3><p className="rm-meta rm-muted">One primary action per group.<br />Native buttons, clear intent.</p></div><div className="spec-stack"><div className="spec-row"><Button onClick={() => setNotice("Primary button activated.")}>Primary action <ArrowRight size={18} aria-hidden="true" /></Button><Button variant="accent" onClick={() => setNotice("Accent button activated.")}>Accent action <Plus size={18} aria-hidden="true" /></Button><Button variant="secondary" onClick={() => setNotice("Secondary button activated.")}>Secondary</Button><Button variant="ghost" onClick={() => setNotice("Quiet button activated.")}>Quiet action</Button></div><div className="spec-row"><Button size="sm" variant="destructive" onClick={() => setNotice("Destructive style activated. This specimen does not delete anything.")}>Destructive</Button><Button disabled>Unavailable</Button><Button loading>Loading</Button><IconButton aria-label="Save specimen" aria-pressed={pressed} variant="secondary" onClick={() => setPressed(!pressed)}><Heart size={19} fill={pressed ? "currentColor" : "none"} /></IconButton><IconButton aria-label="Reset specimen feedback" onClick={() => { setPressed(false); setNotice("Specimen feedback reset."); }}><X size={19} /></IconButton></div><p role="status" className="rm-meta rm-muted">{notice}</p></div></div>
    <div className="spec-component-row"><div><h3 className="rm-heading-sm">Inputs</h3><p className="rm-meta rm-muted">Persistent labels.<br />Helpful hints. Specific errors.</p></div><div className="spec-input-grid"><SearchInput placeholder="Search anything on campus…" hint="Search field specimen; no results are fetched." /><Input label="Email" type="email" autoComplete="off" placeholder="Your email address" leadingIcon={<Mail size={19} />} hint="Supporting text belongs beneath its field." /><Input label="Required field" required value={requiredValue} onChange={event => setRequiredValue(event.target.value)} error={requiredValue.trim() ? undefined : "This field is empty. Add a value to continue."} hint="Type to clear this example error." /><Input label="Unavailable field" placeholder="Not available yet" disabled /></div></div>
  </>;
}
