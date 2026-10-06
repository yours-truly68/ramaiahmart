"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Check,
  Circle,
  GraduationCap,
  Home,
  LogOut,
  MessageSquare,
  Package,
  Pencil,
  Plus,
  ShieldCheck,
  Trash2,
  UserRound,
} from "lucide-react";
import { Avatar, Button, Input, Skeleton, StatusBadge } from "@/components/ui";
import { SiteHeader, SiteFooter } from "@/components/marketplace/site-header";
import { SessionBoundary } from "@/lib/auth/session";
import { api, errorMessage } from "@/lib/api/client";
import type {
  DeletionRequestResponse,
  PostPage,
  PostType,
  User,
  UserPostStats,
} from "@/lib/api/types";
import {
  ListingImage,
  priceLabel,
  relativeTime,
} from "@/features/marketplace/presentation";
import { Dialog } from "@/features/marketplace/dialog";
import { DetailPanel } from "@/features/marketplace/panels";

function EditProfile({ user, close }: { user: User; close: () => void }) {
  const client = useQueryClient();
  const [validation, setValidation] = useState("");
  const [whatsappEnabled, setWhatsappEnabled] = useState(user.whatsapp_enabled ?? false);
  const [whatsappNumber, setWhatsappNumber] = useState(user.whatsapp_number ?? "");
  const save = useMutation({
    mutationFn: (body: object) =>
      api<User>("users/me", { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: (data) => {
      client.setQueryData(["me"], data);
      close();
    },
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = String(data.get("name")).trim();
    if (name.length < 2) {
      setValidation("Please enter at least two characters for your name.");
      return;
    }
    if (whatsappEnabled && !whatsappNumber.trim()) {
      setValidation("Please enter a valid WhatsApp phone number starting with + and country code.");
      return;
    }
    setValidation("");
    save.mutate({
      name,
      bio: String(data.get("bio")).trim(),
      whatsapp_enabled: whatsappEnabled,
      whatsapp_number: whatsappNumber.trim() || null,
    });
  }
  return (
    <Dialog title="A little more you." onClose={close}>
      <p className="panel-intro">
        Help fellow students know who they’re exchanging with.
      </p>
      <form className="panel-form" onSubmit={submit}>
        <Input
          label="Full name"
          name="name"
          autoComplete="name"
          required
          minLength={2}
          maxLength={255}
          defaultValue={user.name}
        />
        <label className="rm-field">
          <span className="rm-label">Short bio</span>
          <textarea
            className="rm-input"
            name="bio"
            rows={4}
            maxLength={500}
            defaultValue={user.bio ?? ""}
          />
          <span className="rm-field-hint">
            Up to 500 characters. A little about you and what you’re into.
          </span>
        </label>

        <div className="rm-field" style={{ marginTop: "16px", paddingTop: "16px", borderTop: "1px solid var(--border)" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer", fontWeight: 600 }}>
            <input
              type="checkbox"
              name="whatsapp_enabled"
              checked={whatsappEnabled}
              onChange={(e) => setWhatsappEnabled(e.target.checked)}
              style={{ width: "16px", height: "16px", accentColor: "var(--accent-orange)" }}
            />
            <span>WhatsApp enquiries</span>
          </label>
          <p className="rm-field-hint" style={{ marginTop: "4px", fontSize: "13px" }}>
            Students can choose to continue an enquiry on WhatsApp. Your number is only used when you enable this.
          </p>

          {whatsappEnabled && (
            <div style={{ marginTop: "12px" }}>
              <label htmlFor="wa-number" className="rm-label">
                WhatsApp phone number <span className="rm-required">(required)</span>
              </label>
              <input
                id="wa-number"
                type="tel"
                className="rm-input"
                name="whatsapp_number"
                placeholder="+91 98765 43210"
                value={whatsappNumber}
                onChange={(e) => setWhatsappNumber(e.target.value)}
                required={whatsappEnabled}
              />
              <span className="rm-field-hint">
                Enter your full international number starting with + (e.g. +91 98765 43210).
              </span>
            </div>
          )}
        </div>

        {(validation || save.isError) && (
          <p className="form-error" role="alert">
            {validation || errorMessage(save.error)}
          </p>
        )}
        <Button variant="accent" type="submit" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save profile"}
          <Check size={17} />
        </Button>
      </form>
    </Dialog>
  );
}

function DeletionModal({
  close,
  onScheduled,
}: {
  close: () => void;
  onScheduled: (data: DeletionRequestResponse) => void;
}) {
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState("");
  const deleteMutation = useMutation({
    mutationFn: () =>
      api<DeletionRequestResponse>("users/me/deletion-request", {
        method: "POST",
      }),
    onSuccess: (data) => {
      onScheduled(data);
      close();
    },
    onError: (err) => {
      setError(errorMessage(err));
    },
  });

  return (
    <Dialog title="Delete account" onClose={close}>
      <div className="deletion-dialog-content">
        <p>
          Your account will enter a <strong>15-day deletion period</strong>. If
          you log in or perform qualifying activity during this period, your
          deletion request will be cancelled. After 15 days without activity,
          your account and associated data will be permanently deleted.
        </p>
        <label className="deletion-confirm-check">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          <span>
            I understand that my account, profile, and all active listings will
            be permanently deleted after 15 days.
          </span>
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="deletion-dialog-actions">
          <Button
            variant="ghost"
            onClick={close}
            disabled={deleteMutation.isPending}
          >
            Keep account
          </Button>
          <Button
            variant="destructive"
            disabled={!confirmed || deleteMutation.isPending}
            onClick={() => deleteMutation.mutate()}
          >
            {deleteMutation.isPending ? "Scheduling…" : "Schedule deletion"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

function Profile({ user }: { user: User }) {
  const [tab, setTab] = useState<PostType>("OFFER");
  const [page, setPage] = useState(1);
  const [edit, setEdit] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [detail, setDetail] = useState<string | null>(null);
  const router = useRouter();
  const client = useQueryClient();

  const posts = useQuery({
    queryKey: ["my-posts", user.id, tab, page],
    queryFn: ({ signal }) =>
      api<PostPage>(`users/me/posts?type=${tab}&page=${page}&page_size=9`, {
        signal,
      }),
  });
  const stats = useQuery({
    queryKey: ["my-stats", user.id],
    queryFn: ({ signal }) =>
      api<UserPostStats>("users/me/stats", { signal }),
  });
  const logout = useMutation({
    mutationFn: () => api("auth/logout", { method: "POST" }),
    onSuccess: () => {
      client.clear();
      router.replace("/login");
    },
  });

  const cancelDeletion = useMutation({
    mutationFn: () =>
      api<User>("users/me/deletion-cancel", { method: "POST" }),
    onSuccess: (updatedUser) => {
      client.setQueryData(["me"], updatedUser);
    },
  });

  const completion = [
    { label: "Add your name", complete: Boolean(user.name) },
    { label: "Write a short bio", complete: Boolean(user.bio?.trim()) },
  ];
  const percentage = Math.round(
    (completion.filter((item) => item.complete).length / completion.length) *
      100,
  );

  function selectTab(value: PostType) {
    setTab(value);
    setPage(1);
  }

  const isPendingDeletion = user.status === "DELETION_PENDING";
  const isInactive = user.status === "INACTIVE";

  return (
    <main id="main" className="profile-layout rm-container">
      <aside className="profile-nav" aria-label="Your marketplace">
        <Link href="/">
          <Home size={19} />
          Browse campus
        </Link>
        <Link href="/messages">
          <MessageSquare size={19} />
          Messages
        </Link>
        <a href="#my-posts" onClick={() => selectTab("OFFER")}>
          <Package size={19} />
          My listings
        </a>
        <a href="#my-posts" onClick={() => selectTab("REQUEST")}>
          <GraduationCap size={19} />
          My requests
        </a>
        <a className="selected" href="#profile-heading" aria-current="page">
          <UserRound size={19} />
          Profile
        </a>
        <Link href="/post/create" className="sidebar-post">
          <Plus size={25} />
          <strong>Post something</strong>
          <span>Give it a new home on campus.</span>
          <ArrowRight size={18} />
        </Link>
        <button
          className="profile-logout"
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
        >
          <LogOut size={17} />
          {logout.isPending ? "Logging out…" : "Log out"}
        </button>
        {logout.isError && (
          <p className="form-error" role="alert">
            {errorMessage(logout.error)}
          </p>
        )}
      </aside>

      <div className="profile-main">
        <section className="profile-identity" aria-labelledby="profile-heading">
          <Avatar
            name={user.name}
            src={user.profile_image_url ?? undefined}
            size="lg"
            className="identity-avatar"
          />
          <div className="identity-copy">
            <p className="eyebrow">Your campus identity</p>
            <h1 id="profile-heading">{user.name}</h1>
            <p className="identity-email">{user.email}</p>
            <span className="university-badge verified">
              <ShieldCheck size={16} />
              Ramaiah student
            </span>
            <p className="identity-bio">
              {user.bio ||
                "A few words about you can help a fellow student say hello."}
            </p>
          </div>
          <Button
            className="edit-profile"
            variant="secondary"
            onClick={() => setEdit(true)}
          >
            <Pencil size={15} />
            Edit Profile
          </Button>
        </section>

        <section className="profile-stats" aria-label="Your marketplace activity">
          {stats.isPending ? (
            <>
              <Skeleton />
              <Skeleton />
              <Skeleton />
            </>
          ) : stats.isError ? (
            <p>
              Activity couldn’t load.{" "}
              <button
                className="inline-link"
                onClick={() => stats.refetch()}
              >
                Retry
              </button>
            </p>
          ) : (
            [
              [stats.data.listings, "Listings"],
              [stats.data.requests, "Requests"],
              [stats.data.published, "Published"],
            ].map(([value, label]) => (
              <div key={label}>
                <strong>{value}</strong>
                <span>{label}</span>
              </div>
            ))
          )}
        </section>

        <div className="profile-content">
          <section id="my-posts" aria-labelledby="my-posts-title">
            <div className="profile-tabs" role="tablist" aria-label="Your posts">
              {(["OFFER", "REQUEST"] as const).map((value) => (
                <button
                  key={value}
                  role="tab"
                  id={`tab-${value}`}
                  aria-controls="my-post-panel"
                  aria-selected={tab === value}
                  tabIndex={tab === value ? 0 : -1}
                  onClick={() => selectTab(value)}
                  onKeyDown={(event) => {
                    if (["ArrowLeft", "ArrowRight"].includes(event.key)) {
                      event.preventDefault();
                      const next = value === "OFFER" ? "REQUEST" : "OFFER";
                      selectTab(next);
                      document.getElementById(`tab-${next}`)?.focus();
                    }
                  }}
                >
                  {value === "OFFER" ? "Listings" : "Requests"}
                </button>
              ))}
            </div>
            <div
              id="my-post-panel"
              role="tabpanel"
              aria-labelledby={`tab-${tab}`}
            >
              <div className="profile-section-heading">
                <h2 id="my-posts-title">
                  {tab === "OFFER" ? "My listings" : "My requests"}
                </h2>
                <Link
                  href={`/post/create?type=${tab}`}
                  className="text-action"
                >
                  Add {tab === "OFFER" ? "listing" : "request"}
                  <Plus size={17} />
                </Link>
              </div>
              {posts.isPending ? (
                <div
                  className="profile-post-grid"
                  aria-busy="true"
                  aria-label="Loading your posts"
                >
                  {Array.from({ length: 3 }, (_, i) => (
                    <div className="post-skeleton" key={i}>
                      <Skeleton shape="image" />
                      <Skeleton />
                      <Skeleton />
                    </div>
                  ))}
                </div>
              ) : posts.isError ? (
                <div className="profile-empty" role="alert">
                  <h3>Let’s get your posts back.</h3>
                  <p>{errorMessage(posts.error)}</p>
                  <Button onClick={() => posts.refetch()}>Try again</Button>
                </div>
              ) : posts.data.items.length ? (
                <>
                  <div className="profile-post-grid">
                    {posts.data.items.map((post) => {
                      const content = (
                        <>
                          <ListingImage post={post} />
                          <div className="owner-card-body">
                            <StatusBadge status={post.status} />
                            <h3>{post.title}</h3>
                            <p className="post-price">
                              {priceLabel(post)}{" "}
                              <span>{post.price_unit}</span>
                            </p>
                            <div className="post-meta">
                              <span>{post.category.name}</span>
                              <time dateTime={post.created_at}>
                                {relativeTime(post.created_at)}
                              </time>
                            </div>
                          </div>
                        </>
                      );
                      return (
                        <article className="owner-card" key={post.id}>
                          {["DRAFT", "REJECTED"].includes(post.status) ? (
                            <Link
                              href={`/post/create?draft=${post.id}`}
                              aria-label={`Continue ${post.title}`}
                            >
                              {content}
                            </Link>
                          ) : (
                            <button
                              onClick={() => setDetail(post.id)}
                              aria-label={`View ${post.title}`}
                            >
                              {content}
                            </button>
                          )}
                        </article>
                      );
                    })}
                  </div>
                  <div className="owner-pagination">
                    <Button
                      variant="ghost"
                      disabled={page === 1}
                      onClick={() => setPage(page - 1)}
                    >
                      Previous
                    </Button>
                    <span>
                      Page {page} of {posts.data.pages}
                    </span>
                    <Button
                      variant="ghost"
                      disabled={page >= posts.data.pages}
                      onClick={() => setPage(page + 1)}
                    >
                      Next
                      <ArrowRight size={16} />
                    </Button>
                  </div>
                </>
              ) : (
                <div className="profile-empty">
                  <Package size={32} strokeWidth={1.3} />
                  <h3>
                    {tab === "OFFER"
                      ? "Your next chapter starts here."
                      : "Put the word out."}
                  </h3>
                  <p>
                    {tab === "OFFER"
                      ? "A spare calculator. Last semester’s books. Something you have could be exactly what another student needs."
                      : "Looking for something? Let fellow students know what would make your campus life a little easier."}
                  </p>
                  <Link
                    href={`/post/create?type=${tab}`}
                    className="rm-button rm-button--primary rm-button--md"
                  >
                    {tab === "OFFER"
                      ? "Create your first listing"
                      : "Post your first request"}
                    <ArrowRight size={17} />
                  </Link>
                </div>
              )}
            </div>
          </section>

          <aside className="profile-asides">
            <section className="profile-aside-card account-lifecycle-card">
              <h2>Account status</h2>
              {isPendingDeletion ? (
                <>
                  <div className="lifecycle-status-row">
                    <span className="lifecycle-status-dot pending" />
                    <strong>Deletion pending</strong>
                  </div>
                  <div className="lifecycle-warning-box">
                    <p>
                      Your account is scheduled for deletion on{" "}
                      <strong>
                        {user.deletion_scheduled_at
                          ? new Date(
                              user.deletion_scheduled_at,
                            ).toLocaleDateString("en-IN", {
                              day: "numeric",
                              month: "short",
                              year: "numeric",
                            })
                          : "in 15 days"}
                      </strong>
                      . Log in or cancel deletion to keep your account.
                    </p>
                  </div>
                  <div className="lifecycle-actions">
                    <button
                      className="lifecycle-cancel-btn"
                      onClick={() => cancelDeletion.mutate()}
                      disabled={cancelDeletion.isPending}
                    >
                      {cancelDeletion.isPending
                        ? "Cancelling…"
                        : "Cancel deletion"}
                    </button>
                  </div>
                </>
              ) : isInactive ? (
                <>
                  <div className="lifecycle-status-row">
                    <span className="lifecycle-status-dot inactive" />
                    <strong>Account inactive</strong>
                  </div>
                  <p className="lifecycle-desc">
                    Your account is inactive due to extended inactivity. There is
                    no penalty. Continue using RamaiahMart to reactivate it.
                  </p>
                  <div className="lifecycle-actions">
                    <button
                      className="lifecycle-delete-btn"
                      onClick={() => setConfirmDelete(true)}
                    >
                      <Trash2 size={14} />
                      Delete account
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="lifecycle-status-row">
                    <span className="lifecycle-status-dot active" />
                    <strong>Account active</strong>
                  </div>
                  <p className="lifecycle-desc">
                    Your account is in good standing on the campus marketplace.
                  </p>
                  <div className="lifecycle-actions">
                    <button
                      className="lifecycle-delete-btn"
                      onClick={() => setConfirmDelete(true)}
                    >
                      <Trash2 size={14} />
                      Delete account
                    </button>
                  </div>
                </>
              )}
            </section>

            <section className="profile-aside-card">
              <div className="completion-heading">
                <h2>Make yourself at home.</h2>
                <strong>{percentage}%</strong>
              </div>
              <progress
                value={percentage}
                max={100}
                aria-label="Profile completion"
              />
              <ul>
                {completion.map((item) => (
                  <li key={item.label}>
                    {item.complete ? (
                      <Check size={16} className="complete-icon" />
                    ) : (
                      <Circle size={15} />
                    )}
                    <span>{item.label}</span>
                  </li>
                ))}
              </ul>
              <button className="inline-link" onClick={() => setEdit(true)}>
                Add a little about you
                <ArrowUpRight size={16} />
              </button>
            </section>

            <section className="joined-card">
              <CalendarDays size={21} />
              <p>
                Joined{" "}
                {new Date(user.created_at).toLocaleDateString("en-IN", {
                  month: "long",
                  year: "numeric",
                })}
              </p>
            </section>
          </aside>
        </div>
      </div>

      {edit && <EditProfile user={user} close={() => setEdit(false)} />}
      {confirmDelete && (
        <DeletionModal
          close={() => setConfirmDelete(false)}
          onScheduled={(data) => {
            client.setQueryData(["me"], (prev: User | undefined) =>
              prev
                ? {
                    ...prev,
                    status: data.status,
                    deletion_requested_at: data.deletion_requested_at,
                    deletion_scheduled_at: data.deletion_scheduled_at,
                  }
                : prev,
            );
          }}
        />
      )}
      {detail && <DetailPanel id={detail} onClose={() => setDetail(null)} />}
    </main>
  );
}

export default function ProfilePage() {
  return (
    <>
      <SiteHeader />
      <SessionBoundary next="/profile">
        {(user) => <Profile user={user} />}
      </SessionBoundary>
      <SiteFooter />
    </>
  );
}
