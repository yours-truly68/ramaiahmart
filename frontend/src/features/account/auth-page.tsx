"use client";
import { useState, type FormEvent } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Eye, EyeOff, GraduationCap, LockKeyhole, Mail, MapPin, Recycle, UserRound } from "lucide-react";
import { api, errorMessage } from "@/lib/api/client";
import type { AuthConfig } from "@/lib/api/types";
import { safeNext } from "@/lib/auth/session";
import { Button, Input } from "@/components/ui";
import { SiteHeader, SiteFooter } from "@/components/marketplace/site-header";
import { Verification } from "./verification";
export default function AuthPage({ mode }: { mode: "login" | "register" }) {
  const registration = mode === "register";
  const router = useRouter();
  const params = useSearchParams();
  const client = useQueryClient();
  const next = safeNext(params.get("next"));
  const [showPassword, setShowPassword] = useState(false);
  const [verification, setVerification] = useState<{ email: string; verification_code: string | null } | null>(null);
  const [validation, setValidation] = useState("");
  const config = useQuery({ queryKey: ["auth-config"], queryFn: ({ signal }) => api<AuthConfig>("auth/config", { signal }) });
  const mutation = useMutation({ mutationFn: (body: object) => api<{ email: string; verification_code: string | null }>(`auth/${mode}`, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: async data => {
      if (registration) setVerification(data);
      else { client.removeQueries({ queryKey: ["my-posts"] }); client.removeQueries({ queryKey: ["my-stats"] }); await client.invalidateQueries({ queryKey: ["me"] }); router.replace(next); }
    },
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setValidation("");
    const form = event.currentTarget;
    const data = new FormData(form);
    const email = String(data.get("email")).trim();
    const password = String(data.get("password"));
    const name = String(data.get("name") ?? "").trim();
    if (registration) {
      if (name.length < 2) { setValidation("Enter your full name using at least two characters."); return; }
      if (password !== data.get("confirm")) { setValidation("Your passwords don’t match. Please check both fields."); return; }
      if (new TextEncoder().encode(password).length > 72) { setValidation("Please use a shorter password (up to 72 UTF-8 bytes)."); return; }
      const domain = email.split("@")[1]?.toLowerCase();
      if (config.data && !config.data.allowed_email_domains.some(allowed => domain === allowed.toLowerCase() || domain?.endsWith(`.${allowed.toLowerCase()}`))) { setValidation("Use your supported university email address to join."); return; }
    }
    mutation.mutate({ email, password, ...(registration ? { name } : {}) }, { onSuccess: () => form.reset() });
  }
  return <><SiteHeader auth={mode} /><main id="main" className={`auth-page rm-container auth-page--${mode}`}>
    <section className="auth-story"><p className="eyebrow">{registration ? "Your campus. Your community." : "Welcome back"}</p><h1>{registration ? <>Join the{" "}<br />RamaiahMart{" "}<br /><em>community.</em></> : <>Good to{" "}<br />see you{" "}<br /><em>again.</em></>}</h1><p className="auth-story-copy">{registration ? "A local marketplace for Ramaiah students. Pass something on, find what you need, and make the most of campus life." : "Your next find could be a few classrooms away. Log in to buy, sell, rent, and connect with fellow Ramaiah students."}</p><div className="auth-story-photo"><Image src="/images/campus-room.png" alt="Books, headphones, and an orange chair in a warm sunlit study room" fill sizes="(max-width: 680px) 100vw, 50vw" priority /><span>Same campus.{" "}<br />New possibilities.</span></div></section>
    <section className="auth-form-card" aria-label={registration ? "Create your account" : "Log in"}>
      {verification ? <Verification email={verification.email} developmentCode={verification.verification_code} /> : <>
        <p className="eyebrow">{registration ? "A little introduction" : "Your corner of campus"}</p><h2>{registration ? "Create your account" : <>Log in to Ramaiah<span>Mart</span></>}</h2><p className="auth-form-intro">{registration ? "Start with your name and university email." : "Pick up where you left off."}</p>
        <form onSubmit={submit} className="panel-form" aria-busy={mutation.isPending}>
          {registration && <Input label="Full name" name="name" autoComplete="name" minLength={2} maxLength={255} leadingIcon={<UserRound size={18} />} placeholder="Your full name" required />}
          <Input label="University email" name="email" type="email" autoComplete="username" maxLength={255} leadingIcon={<Mail size={18} />} placeholder="you@your-university.edu" required hint={registration && config.data ? `Supported: ${config.data.allowed_email_domains.map(domain => `@${domain}`).join(", ")}` : undefined} />
          <div className="password-field"><Input label="Password" name="password" type={showPassword ? "text" : "password"} autoComplete={registration ? "new-password" : "current-password"} minLength={registration ? config.data?.password_min_length ?? 8 : undefined} maxLength={registration ? 72 : undefined} leadingIcon={<LockKeyhole size={18} />} required hint={registration ? `Use at least ${config.data?.password_min_length ?? 8} characters.` : undefined} /><button type="button" className="password-toggle" aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={19} /> : <Eye size={19} />}</button></div>
          {registration && <Input label="Confirm password" name="confirm" type={showPassword ? "text" : "password"} autoComplete="new-password" leadingIcon={<LockKeyhole size={18} />} required />}
          {(validation || mutation.isError) && <p className="form-error" role="alert">{validation || errorMessage(mutation.error)}</p>}
          {registration && config.isError && <p className="form-error" role="alert">We couldn’t load the university requirements. <button type="button" className="inline-link" onClick={() => config.refetch()}>Try again</button></p>}
          <Button type="submit" variant="accent" disabled={mutation.isPending || (registration && !config.data)}>{mutation.isPending ? (registration ? "Creating your account…" : "Logging in…") : registration ? "Create account" : "Log in"}<ArrowRight size={18} /></Button>
        </form>
        {registration && <p className="auth-fine-print">For Ramaiah students. You’ll verify your university email before publishing your first post.</p>}
        <p className="auth-switch">{registration ? "Already have an account?" : "New to RamaiahMart?"} <Link href={`${registration ? "/login" : "/register"}?next=${encodeURIComponent(next)}`}>{registration ? "Log in" : "Create an account"}<ArrowRight size={14} /></Link></p>
      </>}
    </section>
  </main><section className="auth-benefits rm-container" aria-label="Made for student life"><div><GraduationCap size={24} /><h3>Built for Ramaiah</h3><p>Your university community, in one place.</p></div><div><Recycle size={24} /><h3>A second semester</h3><p>Give useful things another chapter.</p></div><div><MapPin size={24} /><h3>Keep it on campus</h3><p>Discover what’s already around you.</p></div></section><SiteFooter /></>;
}
