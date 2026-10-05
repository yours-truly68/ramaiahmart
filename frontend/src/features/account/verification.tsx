"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { api, errorMessage } from "@/lib/api/client";
import type { AuthConfig } from "@/lib/api/types";
import { Button, Input } from "@/components/ui";
export function Verification({ email, developmentCode, onDone }: { email: string; developmentCode?: string | null; onDone?: () => void }) {
  const client = useQueryClient();
  const [code, setCode] = useState("");
  const config = useQuery({ queryKey: ["auth-config"], queryFn: () => api<AuthConfig>("auth/config") });
  const mutation = useMutation({ mutationFn: () => api("auth/verify", { method: "POST", body: JSON.stringify({ email, code: code.trim() }) }), onSuccess: async () => { await client.invalidateQueries({ queryKey: ["me"] }); onDone?.(); } });
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); mutation.mutate(); }
  if (mutation.isSuccess) return <div className="verification-success"><ShieldCheck size={38} /><h2>You’re Ramaiah verified.</h2><p>Your university email is verified. You’re ready to join the campus exchange.</p><Link className="rm-button rm-button--accent rm-button--md" href="/login">Log in to continue<ArrowRight size={17} /></Link></div>;
  return <div className="verification-form"><span className="verification-mark"><ShieldCheck size={25} /></span><h2>Make it campus official.</h2><p>Verify <strong>{email}</strong> before publishing a post.</p>
    {developmentCode ? <p className="development-code">Local development code: <strong>{developmentCode}</strong><span>This installation provides the code here instead of sending email.</span></p> : config.data && !config.data.email_delivery_available ? <p className="verification-notice">Email delivery isn’t available on this installation. Your account is saved; ask the administrator for your verification code.</p> : <p>Enter your university verification code below.</p>}
    <form className="panel-form" onSubmit={submit}><Input label="Verification code" autoComplete="one-time-code" inputMode="numeric" minLength={6} maxLength={64} required value={code} onChange={event => setCode(event.target.value)} />{mutation.isError && <p className="form-error" role="alert">{errorMessage(mutation.error)}</p>}<Button type="submit" variant="accent" disabled={mutation.isPending}>{mutation.isPending ? "Verifying…" : "Verify university email"}<ArrowRight size={18} /></Button></form>
  </div>;
}
