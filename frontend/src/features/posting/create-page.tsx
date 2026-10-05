"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import Image from "next/image";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Camera, Check, CircleCheck, Clock3, FileText, ImagePlus, ShieldCheck, Tag, Trash2, TriangleAlert, X } from "lucide-react";
import { Badge, Button, Input, Skeleton, StatusBadge } from "@/components/ui";
import { SiteHeader, SiteFooter } from "@/components/marketplace/site-header";
import { api, errorMessage } from "@/lib/api/client";
import { SessionBoundary } from "@/lib/auth/session";
import type { Category, MediaConfig, Post, PostImage, PostType, User } from "@/lib/api/types";
import { categoryStyle, priceLabel } from "@/features/marketplace/presentation";

type FormValues = { type: PostType | null; category_id: string; title: string; description: string; price: string; price_unit: string };
type Upload = { id: string; file: File; url: string; state: "ready" | "uploading" | "error"; error?: string; storageKey?: string; uploaded?: boolean };
const steps = ["Type", "Details", "Photos", "Review"];
function Result({ post, edit }: { post: Post; edit: () => void }) {
  const published = post.status === "PUBLISHED";
  const rejected = post.status === "REJECTED";
  return <main id="main" className={`submission-result ${rejected ? "result-rejected" : ""}`} aria-live="polite">{published ? <CircleCheck size={45} /> : rejected ? <TriangleAlert size={45} /> : <Clock3 size={45} />}<StatusBadge status={post.status} /><h1>{published ? "Hello, campus." : rejected ? "This one needs a rethink." : "Your post is in good hands."}</h1><p>{published ? `“${post.title}” is published. Fellow students can now find it in the marketplace.` : rejected ? "Your post wasn’t approved. It isn’t visible in the marketplace. Review the title, description, and photos before trying again." : `“${post.title}” is waiting for moderation. It isn’t published yet. You can check its status in your profile.`}</p><div className="result-actions"><Link href="/profile" className="rm-button rm-button--primary rm-button--md">View my posts<ArrowRight size={17} /></Link>{published && <Link href={`/?post=${post.id}`} className="rm-button rm-button--secondary rm-button--md">See your post</Link>}{rejected && <Button variant="secondary" onClick={edit}>Review and edit</Button>}</div></main>;
}
function Wizard({ user, initial, initialType, resumePhotos }: { user: User; initial?: Post; initialType: PostType | null; resumePhotos: boolean }) {
  const [values, setValues] = useState<FormValues>({ type: initial?.type ?? initialType, category_id: initial?.category.id ?? "", title: initial?.title ?? "", description: initial?.description ?? "", price: initial?.price ?? "", price_unit: initial?.price_unit ?? "" });
  const [draftId, setDraftId] = useState(initial?.id ?? "");
  const [step, setStep] = useState(initial ? (resumePhotos ? 2 : 1) : 0);
  const [images, setImages] = useState<PostImage[]>(initial?.images ?? []);
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Post | null>(initial && !["DRAFT", "REJECTED"].includes(initial.status) ? initial : null);
  const objectUrls = useRef(new Set<string>());
  const heading = useRef<HTMLHeadingElement>(null);
  const client = useQueryClient();
  const categories = useQuery({ queryKey: ["categories"], queryFn: ({ signal }) => api<Category[]>("categories", { signal }), staleTime: 300000 });
  const mediaConfig = useQuery({ queryKey: ["media-config"], queryFn: ({ signal }) => api<MediaConfig>("media/config", { signal }), staleTime: 300000 });
  useEffect(() => { const urls = objectUrls.current; return () => { urls.forEach(URL.revokeObjectURL); }; }, []);
  useEffect(() => { heading.current?.focus(); }, [step]);
  const category = categories.data?.find(item => item.id === values.category_id);
  const sortedCategories = [...(categories.data ?? [])].sort((a, b) => categoryStyle(a.slug).order - categoryStyle(b.slug).order || a.name.localeCompare(b.name));
  const picture = uploads[0]?.url ?? images[0]?.public_url;
  const previewPrice = values.price ? priceLabel({ price: values.price, type: values.type ?? "OFFER" } as Post) : values.type === "REQUEST" ? "Budget open" : "Your price";
  function update<K extends keyof FormValues>(key: K, value: FormValues[K]) { setValues(previous => ({ ...previous, [key]: value })); setError(""); }
  async function saveDetails(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (values.title.trim().length < 3 || values.description.trim().length < 5) { setError("Use at least 3 characters for the title and 5 for the description, excluding spaces."); return; }
    if (!values.type || !values.category_id) { setError("Choose a post type and category first."); return; }
    setBusy(true);
    const body = { category_id: values.category_id, title: values.title.trim(), description: values.description.trim(), price: values.price || null, price_unit: values.price_unit.trim() || null };
    try {
      const saved = await api<Post>(draftId ? `posts/${draftId}` : "posts", { method: draftId ? "PATCH" : "POST", body: JSON.stringify(draftId ? body : { ...body, type: values.type }) });
      setDraftId(saved.id);
      window.history.replaceState(null, "", `/post/create?draft=${saved.id}&step=photos`);
      await client.invalidateQueries({ queryKey: ["my-posts"] });
      await client.invalidateQueries({ queryKey: ["my-stats"] });
      setStep(2);
    } catch (failure) { setError(errorMessage(failure)); }
    finally { setBusy(false); }
  }
  function chooseFiles(files: FileList | null) {
    if (!files || !mediaConfig.data) return;
    setError("");
    const next: Upload[] = [];
    const failures: string[] = [];
    for (const file of Array.from(files)) {
      if (!mediaConfig.data.content_types.includes(file.type)) { failures.push(`${file.name}: choose a JPEG, PNG, or WebP image.`); continue; }
      if (file.size === 0 || file.size > mediaConfig.data.max_file_size) { failures.push(`${file.name}: the image must be under ${Math.round(mediaConfig.data.max_file_size / 1024 / 1024)} MB and not empty.`); continue; }
      const url = URL.createObjectURL(file); objectUrls.current.add(url);
      next.push({ id: crypto.randomUUID(), file, url, state: "ready" });
    }
    setUploads(previous => [...previous, ...next]);
    if (failures.length) setError(failures.join(" "));
  }
  function patchUpload(id: string, patch: Partial<Upload>) { setUploads(previous => previous.map(item => item.id === id ? { ...item, ...patch } : item)); }
  async function uploadOne(item: Upload): Promise<boolean> {
    patchUpload(item.id, { state: "uploading", error: undefined });
    let key = item.storageKey;
    try {
      if (!item.uploaded || !key) {
        const credentials = await api<{ upload_url: string; storage_key: string }>("media/upload-url", { method: "POST", body: JSON.stringify({ post_id: draftId, content_type: item.file.type, file_size: item.file.size }) });
        key = credentials.storage_key;
        const uploaded = await fetch(credentials.upload_url, { method: "PUT", headers: { "Content-Type": item.file.type }, body: item.file, signal: AbortSignal.timeout(120000) });
        if (!uploaded.ok) throw new Error("Upload failed");
        patchUpload(item.id, { storageKey: key, uploaded: true });
      }
      let attached: PostImage;
      try { attached = await api<PostImage>("media/complete", { method: "POST", body: JSON.stringify({ post_id: draftId, storage_key: key }) }); }
      catch (failure) {
        // Reconcile a completion that succeeded but whose response was lost.
        const current = await api<Post>(`posts/${draftId}`);
        const found = current.images.find(image => image.storage_key === key);
        if (!found) throw failure;
        attached = found;
      }
      setImages(previous => [...previous.filter(image => image.id !== attached.id), attached]);
      setUploads(previous => previous.filter(upload => upload.id !== item.id));
      URL.revokeObjectURL(item.url); objectUrls.current.delete(item.url);
      return true;
    } catch { patchUpload(item.id, { state: "error", error: "Upload couldn’t finish. Check your connection and retry, or remove this photo." }); return false; }
  }
  async function reviewPhotos() {
    setError("");
    if (values.type === "OFFER" && !images.length && !uploads.length) { setError("Add at least one photo so fellow students can see what you’re offering."); return; }
    setBusy(true);
    let success = true;
    for (const item of uploads) { if (!await uploadOne(item)) success = false; }
    setBusy(false);
    if (success) setStep(3);
  }
  async function removeImage(image: PostImage) {
    setBusy(true); setError("");
    try { await api(`media/${image.id}`, { method: "DELETE" }); setImages(previous => previous.filter(item => item.id !== image.id)); }
    catch (failure) { setError(errorMessage(failure)); }
    finally { setBusy(false); }
  }
  async function publish() {
    setBusy(true); setError("");
    try {
      const posted = await api<Post>(`posts/${draftId}/publish`, { method: "POST" });
      setResult(posted);
      await client.invalidateQueries({ queryKey: ["my-posts"] }); await client.invalidateQueries({ queryKey: ["my-stats"] }); await client.invalidateQueries({ queryKey: ["posts"] });
    } catch (failure) {
      try {
        const current = await api<Post>(`posts/${draftId}`);
        if (!["DRAFT", "REJECTED"].includes(current.status)) setResult(current);
        else setError(errorMessage(failure));
      } catch { setError(errorMessage(failure)); }
    } finally { setBusy(false); }
  }
  if (result) return <Result post={result} edit={() => { setResult(null); setStep(1); }} />;
  return <main id="main" className="create-layout rm-container"><aside className="create-story"><Link href="/profile" className="back-link"><ArrowLeft size={17} />Back to profile</Link><p className="eyebrow">A little campus possibility</p><h1>{values.type === "REQUEST" ? <>What you need.{" "}<br />Closer than{" "}<br />you think.</> : <>Give your{" "}<br />item a{" "}<br />new home.</>}</h1><p>{values.type === "REQUEST" ? "Put the word out. A fellow student might have just what you’re looking for." : "Turn what you no longer need into a new possibility for another Ramaiah student."}</p><div className="create-story-photo"><Image src="/images/campus-room.png" alt="Books and headphones ready for another semester" fill sizes="25vw" /><span>Same campus.{" "}<br />New possibilities.</span></div></aside>
    <section className="create-workspace"><ol className="create-steps" aria-label="Create post progress">{steps.map((label, index) => <li key={label} aria-current={step === index ? "step" : undefined}><button disabled={busy || index > step} onClick={() => { setError(""); setStep(index); }}><span>{index < step ? <Check size={16} /> : index + 1}</span>{label}</button></li>)}</ol>
      <div className="step-content" aria-busy={busy}><p className="eyebrow">Step {step + 1} of 4{draftId ? " · Draft saved" : ""}</p><h2 ref={heading} tabIndex={-1}>{["What are you posting?", values.type === "REQUEST" ? "Tell campus what you need." : "Tell us a little about it.", "Let the photos do the talking.", "One last look."][step]}</h2>
      {step === 0 && <><p className="step-description">Two ways to make campus a little more useful.</p><div className="create-type-choices">{(["OFFER", "REQUEST"] as const).map(value => <button key={value} className={`create-type-choice ${values.type === value ? "type-active" : ""}`} aria-pressed={values.type === value} disabled={Boolean(draftId) && values.type !== value} onClick={() => update("type", value)}><span className="type-icon">{value === "OFFER" ? <Tag size={31} /> : <FileText size={31} />}</span><strong>{value === "OFFER" ? "I HAVE SOMETHING" : "I NEED SOMETHING"}</strong><span>{value === "OFFER" ? "Sell, rent, or offer something you own." : "Request an item or something useful."}</span><span className="type-radio" aria-hidden="true">{values.type === value && <Check size={14} />}</span></button>)}</div>{draftId && <p className="panel-note">A saved draft keeps its original post type. <a href="/post/create">Start a new post</a> to choose a different type.</p>}<div className="step-buttons"><Link href="/" className="text-action">Cancel</Link><Button variant="accent" disabled={!values.type} onClick={() => setStep(1)}>Next: Details<ArrowRight size={17} /></Button></div></>}
      {step === 1 && <form className="create-details" onSubmit={saveDetails}><p className="step-description">Just the details a fellow student needs. Fields marked required must be filled in.</p>
        {categories.isPending ? <Skeleton /> : categories.isError ? <div role="alert"><p className="form-error">Categories couldn’t load.</p><Button onClick={() => categories.refetch()}>Retry</Button></div> : <div className="rm-field"><span className="rm-label">Category <span className="rm-required">(required)</span></span>
          <div className="create-category-tiles">{sortedCategories.map(item => { const { icon: Icon } = categoryStyle(item.slug); const isSelected = values.category_id === item.id; return <button type="button" key={item.id} className={`create-category-chip ${isSelected ? "is-selected" : ""}`} onClick={() => update("category_id", item.id)}><Icon size={16} aria-hidden="true" />{item.name}</button>; })}</div>
          <select className="rm-input" style={{ marginTop: "6px" }} value={values.category_id} required onChange={event => update("category_id", event.target.value)}><option value="" disabled>Or choose from list</option>{sortedCategories.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select>
        </div>}
        <Input label={values.type === "OFFER" ? "What are you offering?" : "What are you looking for?"} value={values.title} minLength={3} maxLength={255} required onChange={event => update("title", event.target.value)} placeholder={values.type === "OFFER" ? "e.g. MacBook Air M1, Good Condition" : "e.g. Looking for a Casio calculator"} hint={`${values.title.length}/255 characters`} />
        <label className="rm-field"><span className="rm-label">Description <span className="rm-required">(required)</span></span><textarea className="rm-input" rows={5} minLength={5} required value={values.description} onChange={event => update("description", event.target.value)} placeholder={values.type === "OFFER" ? "Describe your item, condition, what’s included, and any other details..." : "What you’re looking for and any details that would help."} /></label>
        <div className="price-fields"><Input label={values.type === "OFFER" ? "Price (₹)" : "Budget (₹) — optional"} type="number" min="0" max="9999999999.99" step="0.01" required={values.type === "OFFER"} value={values.price} onChange={event => update("price", event.target.value)} placeholder="e.g. 45000" hint={values.type === "OFFER" ? "Enter 0 if you’re giving it away." : "Leave blank if you’re open to suggestions."} /><Input label="Price unit — optional" maxLength={50} placeholder="e.g. per day, per semester" value={values.price_unit} onChange={event => update("price_unit", event.target.value)} /></div>
        <div className="step-buttons"><Button variant="ghost" onClick={() => setStep(0)} disabled={busy}><ArrowLeft size={16} />Back</Button><Button type="submit" variant="accent" disabled={busy || !categories.data}>{busy ? "Saving your draft…" : "Next: Add Photos"}<ArrowRight size={17} /></Button></div>
      </form>}
      {step === 2 && <><p className="step-description">{values.type === "OFFER" ? "Add at least one clear photo of what you’re offering." : "A photo can help explain your request. This step is optional."} Photos stay with your private draft until you submit.</p>
        {mediaConfig.isPending ? <Skeleton shape="image" /> : mediaConfig.isError ? <div role="alert"><p className="form-error">We couldn’t load upload requirements.</p><Button onClick={() => mediaConfig.refetch()}>Try again</Button></div> : <label className={`upload-zone ${busy ? "upload-disabled" : ""}`}><ImagePlus size={34} strokeWidth={1.4} /><strong>Add your photos</strong><span>JPEG, PNG, or WebP · up to {Math.round(mediaConfig.data.max_file_size / 1024 / 1024)} MB each</span><input aria-label="Choose photos" type="file" accept={mediaConfig.data.content_types.join(",")} multiple disabled={busy} onChange={event => { chooseFiles(event.target.files); event.target.value = ""; }} /></label>}
        <div className="upload-grid">{images.map(image => <div className="uploaded-photo" key={image.id}>{image.public_url && <Image unoptimized src={image.public_url} alt="Uploaded listing photo" width={200} height={160} />}<span><Check size={13} />Uploaded</span><button disabled={busy} aria-label="Remove uploaded photo" onClick={() => removeImage(image)}><Trash2 size={16} /></button></div>)}{uploads.map(item => <div className="uploaded-photo" key={item.id}><Image unoptimized src={item.url} alt={`Selected: ${item.file.name}`} width={200} height={160} /><span>{item.state === "uploading" ? "Uploading…" : item.state === "error" ? "Upload failed" : "Ready to upload"}</span><button disabled={busy} aria-label={`Remove ${item.file.name}`} onClick={() => { setUploads(previous => previous.filter(upload => upload.id !== item.id)); URL.revokeObjectURL(item.url); objectUrls.current.delete(item.url); }}><X size={16} /></button>{item.error && <p className="form-error" role="alert">{item.error}</p>}</div>)}</div>
        <div className="step-buttons"><Button variant="ghost" disabled={busy} onClick={() => setStep(1)}><ArrowLeft size={16} />Back</Button><Button variant="accent" disabled={busy || !mediaConfig.data} onClick={reviewPhotos}>{busy ? "Uploading photos…" : uploads.length ? "Upload & review" : "Next: Review"}<ArrowRight size={17} /></Button></div>
      </>}
      {step === 3 && <><p className="step-description">Here’s what fellow students will see. Check the details before submitting for moderation.</p><dl className="review-details"><div><dt>Post type</dt><dd>{values.type === "OFFER" ? "I have something · Offer" : "I need something · Request"}</dd></div><div><dt>Category</dt><dd>{category?.name}</dd></div><div><dt>Title</dt><dd>{values.title}</dd></div><div><dt>Description</dt><dd className="review-description">{values.description}</dd></div><div><dt>{values.type === "OFFER" ? "Price" : "Budget"}</dt><dd>{previewPrice} {values.price_unit}</dd></div><div><dt>Photos</dt><dd>{images.length} uploaded</dd></div></dl><div className="moderation-note"><ShieldCheck size={22} /><p>Every submission goes through moderation. We’ll show you whether it’s published, waiting for review, or needs changes.</p></div>{!user.university_verified && <p className="verification-notice">Your draft is saved. <Link href="/profile">Verify your university email in your profile</Link> before submitting.</p>}<div className="step-buttons"><Button variant="ghost" disabled={busy} onClick={() => setStep(2)}><ArrowLeft size={16} />Back</Button><Button variant="accent" disabled={busy || !user.university_verified} onClick={publish}>{busy ? "Submitting for review…" : "Submit post"}<ArrowRight size={17} /></Button></div></>}
      {error && <p className="form-error step-error" role="alert">{error}</p>}
      {draftId && <p className="draft-note">Your draft is saved to your profile. You can come back to it later.</p>}
      </div></section>
    <aside className="create-preview"><h2>Preview</h2><p className="preview-subtitle">A little glimpse of your post.</p><article className="live-preview-card"><div className={`preview-photo tone-${category ? categoryStyle(category.slug).tone : "stone"}`}>{picture ? <Image unoptimized key={picture} src={picture} alt="Your post preview" fill sizes="320px" /> : <><Camera size={37} strokeWidth={1.3} /><span>Your photo goes here</span></>}</div><div className="preview-body"><Badge tone={values.type === "REQUEST" ? "request" : "offer"}>{values.type ?? "YOUR POST"}</Badge><h3>{values.title || (values.type === "REQUEST" ? "What you’re looking for" : "Your next campus find")}</h3><p className="preview-price">{previewPrice} <span>{values.price_unit}</span></p><div className="post-meta" style={{ marginTop: "10px" }}><span className="preview-category">{category?.name || "Choose a category"}</span><span>📍 MSRIT</span></div></div></article><div className="posting-tips"><h3>A good post goes a long way.</h3><div><Camera size={20} /><p><strong>Keep it clear.</strong>Natural light and a simple background help.</p></div><div><FileText size={20} /><p><strong>Keep it honest.</strong>Mention the condition and what’s included.</p></div><div><ShieldCheck size={20} /><p><strong>Keep it local.</strong>Arrange to meet in a public place on campus.</p></div></div></aside>
  </main>;
}
function CreateContent({ user }: { user: User }) {
  const params = useSearchParams();
  const initialId = params.get("draft");
  const initialType = params.get("type") === "REQUEST" ? "REQUEST" : params.get("type") === "OFFER" ? "OFFER" : null;
  const draft = useQuery({ queryKey: ["edit-post", initialId, user.id], queryFn: ({ signal }) => api<Post>(`posts/${initialId}`, { signal }), enabled: Boolean(initialId) });
  if (initialId && draft.isPending) return <main id="main" className="rm-container session-state" aria-busy="true"><Skeleton /><Skeleton shape="image" /></main>;
  if (initialId && (draft.isError || draft.data?.author.id !== user.id)) return <main id="main" className="rm-container session-state"><h1>This draft isn’t available.</h1><p>{draft.isError ? errorMessage(draft.error) : "You can only continue your own posts."}</p><Link href="/profile">Back to your profile</Link></main>;
  return <Wizard key={initialId ?? `new-${initialType}`} user={user} initial={draft.data} initialType={initialType} resumePhotos={params.get("step") === "photos"} />;
}
export default function CreatePage() {
  const params = useSearchParams();
  const next = `/post/create${params.size ? `?${params}` : ""}`;
  return <><SiteHeader /><SessionBoundary next={next}>{user => <CreateContent user={user} />}</SessionBoundary><SiteFooter /></>;
}
