"use client";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowRight, ArrowUpRight, MapPin, Plus, Search, Tag, X } from "lucide-react";
import { api } from "@/lib/api/client";
import type { Category, Post, PostPage, PostType } from "@/lib/api/types";
import { Button, Skeleton } from "@/components/ui";
import { categoryStyle, categoryStyles, ListingImage, priceLabel, relativeTime } from "./presentation";
import { DetailPanel } from "./panels";
import { HowItWorks } from "./how-it-works";
import { SiteHeader, SiteFooter } from "@/components/marketplace/site-header";

function SearchForm({ value, onSearch }: { value: string; onSearch: (value: string) => void }) {
  const [input, setInput] = useState(value);
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); onSearch(input.trim()); }
  return <form role="search" className="hero-search" onSubmit={submit}><Search size={21} aria-hidden="true" /><label className="sr-only" htmlFor="market-search">Search the marketplace</label><input id="market-search" name="q" type="search" maxLength={200} value={input} onChange={event => setInput(event.target.value)} placeholder="Search for anything on campus..." /><button type="submit" aria-label="Search marketplace"><ArrowRight size={23} /></button></form>;
}
function PostCard({ post, href }: { post: Post; href: string }) {
  const isOffer = post.type === "OFFER";
  const { tone } = categoryStyle(post.category.slug);
  const isFree = isOffer && post.price !== null && Number(post.price) === 0;

  return (
    <article className={`post-card ${isOffer ? "post-card--offer" : "post-card--request"}`}>
      <Link href={href} scroll={false} className="post-card-link">
        <div className="post-card-visual">
          <ListingImage post={post} />
          <div className="post-card-badges">
            <span className={`post-type-tag ${isOffer ? "post-type-tag--offer" : "post-type-tag--request"}`}>
              <span className="post-type-tag-dot" aria-hidden="true" />
              {isOffer ? "Offer" : "Request"}
            </span>
            <span className={`post-category-tag tone-${tone}`}>
              {post.category.name}
            </span>
          </div>
        </div>
        <div className="post-card-info">
          <h3 className="post-title" title={post.title}>{post.title}</h3>
          <div className="post-price post-card-pricing">
            {isOffer ? (
              isFree ? (
                <span className="post-price-free">Free</span>
              ) : (
                <div className="post-price-wrap">
                  <span className="post-price-amount">{priceLabel(post)}</span>
                  {post.price_unit && <span className="post-price-unit">{post.price_unit}</span>}
                </div>
              )
            ) : (
              <div className="post-request-budget">
                {post.price !== null && Number(post.price) > 0 ? (
                  <span className="post-budget-pill">
                    <span className="post-budget-pill-label">Budget</span>
                    <span className="post-budget-pill-val">{priceLabel(post)}</span>
                  </span>
                ) : (
                  <span className="post-budget-pill post-budget-pill--open">
                    {post.price !== null && Number(post.price) === 0 ? "Looking to borrow" : "Budget open"}
                  </span>
                )}
                {post.price_unit && <span className="post-price-unit">{post.price_unit}</span>}
              </div>
            )}
          </div>
          <div className="post-meta post-card-footer">
            <span className="post-location">
              <MapPin size={12} aria-hidden="true" />
              <span>MSRIT</span>
            </span>
            <time className="post-time" dateTime={post.created_at}>
              {relativeTime(post.created_at)}
            </time>
          </div>
        </div>
      </Link>
    </article>
  );
}
export function FeedSkeleton() {
  return <div className="post-grid" aria-label="Loading recently posted items" aria-busy="true">{Array.from({ length: 6 }, (_, i) => <div className="post-skeleton" key={i}><Skeleton shape="image" /><Skeleton /><Skeleton /><Skeleton /></div>)}</div>;
}
export default function Home() {
  const router = useRouter();
  const params = useSearchParams();
  const q = params.get("q")?.slice(0, 200) ?? "";
  const category = params.get("category") ?? "";
  const type: PostType = params.get("type") === "REQUEST" ? "REQUEST" : "OFFER";
  const detail = params.get("post");
  const categories = useQuery({ queryKey: ["categories"], queryFn: ({ signal }) => api<Category[]>("categories", { signal }), staleTime: 300000 });
  const orderedCategories = useMemo(() => [...(categories.data ?? [])].sort((a, b) => categoryStyle(a.slug).order - categoryStyle(b.slug).order || a.name.localeCompare(b.name)), [categories.data]);
  const featuredCategories = orderedCategories.filter(item => categoryStyles[item.slug]);
  const tiles = featuredCategories.length ? featuredCategories : orderedCategories.slice(0, 9);
  const posts = useInfiniteQuery({
    queryKey: ["posts", q, category, type], initialPageParam: 1,
    queryFn: ({ pageParam, signal }) => {
      const query = new URLSearchParams({ page: String(pageParam), page_size: "12" });
      if (q) query.set("q", q);
      if (category) query.set("category_slug", category);
      if (type) query.set("type", type);
      return api<PostPage>(`posts?${query}`, { signal });
    },
    getNextPageParam: last => last.page < last.pages ? last.page + 1 : undefined,
  });
  const items = posts.data?.pages.flatMap(page => page.items) ?? [];
  const total = posts.data?.pages[0].total ?? 0;
  const filtered = Boolean(q || category);
  const categoryName = categories.data?.find(item => item.slug === category)?.name;
  function url(changes: Record<string, string>) {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) { if (value) next.set(key, value); else next.delete(key); }
    return `/${next.size ? `?${next}` : ""}`;
  }
  function filter(changes: Record<string, string>) { router.push(`${url({ ...changes, post: "" })}#recent`, { scroll: true }); }
  function post(value: PostType | null) { router.push(`/post/create${value ? `?type=${value}` : ""}`); }
  function scrollToHash(event: React.MouseEvent<HTMLAnchorElement>, id: string) {
    event.preventDefault();
    const el = document.getElementById(id);
    if (el) {
      const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      el.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth", block: "start" });
      window.history.pushState(null, "", `#${id}`);
    }
  }
  return <>
    <SiteHeader />
    <main id="main" className="market-home">
      <section className="market-hero rm-container" aria-labelledby="hero-title"><div className="hero-copy"><p className="eyebrow">A MARKETPLACE BY RAMAIAH STUDENTS</p><h1 id="hero-title">The stuff you need.<br />Already on campus.</h1><p className="hero-description">Buy, sell, or rent books, electronics, furniture, notes and more with fellow Ramaiah students.</p><div className="hero-actions"><SearchForm key={q} value={q} onSearch={value => filter({ q: value })} /><a href="#categories" className="browse-categories" onClick={e => scrollToHash(e, "categories")}>Browse categories<ArrowRight size={19} aria-hidden="true" /></a></div></div><div className="hero-photo"><Image src="/images/campus-room.png" alt="Sunlit student room with an orange chair, textbooks, headphones, and a study desk" fill priority sizes="(max-width: 640px) 100vw, 45vw" /><span className="hero-photo-caption">Same campus.<br />New possibilities.</span></div></section>
      <section id="categories" className="categories-section rm-container" aria-label="Browse by category"><div className="mobile-section-heading"><h2>Categories</h2></div>
        {categories.isPending ? <div className="category-row" aria-busy="true" aria-label="Loading categories">{Array.from({ length: 9 }, (_, i) => <Skeleton className="category-skeleton" key={i} />)}</div> : categories.isError ? <div className="inline-error" role="alert"><p>Categories couldn’t load. You can still browse the feed below.</p><button className="text-action" onClick={() => categories.refetch()}>Retry categories<ArrowRight size={17} /></button></div> : tiles.length ? <div className="category-row">{tiles.map((item, index) => { const { icon: Icon, tone } = categoryStyle(item.slug); return <a href={`${url({ category: item.slug, post: "" })}#recent`} key={item.id} className={`category-tile tone-${tone} ${category === item.slug ? "category-selected" : ""}`} aria-current={category === item.slug ? "true" : undefined} onClick={event => { if (!event.metaKey && !event.ctrlKey && !event.shiftKey) { event.preventDefault(); filter({ category: item.slug }); } }}><span className="category-number">0{index + 1}</span><Icon className="category-icon" size={34} strokeWidth={1.6} aria-hidden="true" /><span className="category-bottom"><strong>{item.name}</strong></span></a>; })}</div> : <p className="rm-muted">Campus categories are being put together. Browse all posts below.</p>}
      </section>
      <section className="market-actions rm-container" aria-label="Post to the marketplace"><button className="market-action action-have" onClick={() => post("OFFER")}><span className="action-symbol"><Tag size={26} strokeWidth={1.5} aria-hidden="true" /></span><span><strong>I HAVE SOMETHING</strong><span>Sell or rent an item you own</span></span><ArrowUpRight size={25} aria-hidden="true" /></button><button className="market-action action-need" onClick={() => post("REQUEST")}><span className="action-symbol"><Search size={26} strokeWidth={1.5} aria-hidden="true" /></span><span><strong>I NEED SOMETHING</strong><span>Request an item or service</span></span><ArrowUpRight size={25} aria-hidden="true" /></button></section>
      <section id="recent" className="recent-section rm-container" aria-labelledby="recent-heading"><div className="feed-heading"><div><h2 id="recent-heading">{q ? `Results for “${q}”` : categoryName ? `Fresh in ${categoryName}` : type === "OFFER" ? "Latest offers" : "Latest requests"}</h2></div><a href="#recent" className="browse-categories" onClick={e => scrollToHash(e, "recent")}>View all <ArrowRight size={16} aria-hidden="true" /></a></div>
        <div className="feed-controls"><div className="type-filters" aria-label="Filter post type">{[["OFFER", "Offers"], ["REQUEST", "Requests"]].map(([value, label]) => <button key={value} aria-pressed={type === value} onClick={() => filter({ type: value })}>{label}</button>)}</div><div className="category-filter"><label className="sr-only" htmlFor="category-filter">Filter category</label><select id="category-filter" value={category} onChange={event => filter({ category: event.target.value })}><option value="">All categories</option>{orderedCategories.map(item => <option key={item.id} value={item.slug}>{item.name}</option>)}</select><span className="sort-label">Newest first<ArrowDown size={13} aria-hidden="true" /></span></div></div>
        {filtered && <div className="filter-summary"><p>{posts.isPending ? "Finding your campus matches…" : `${total} ${total === 1 ? "post" : "posts"}`}{categoryName ? ` in ${categoryName}` : ""}</p><button className="text-action" onClick={() => filter({ q: "", category: "" })}>Clear filters<X size={15} /></button></div>}
        {posts.isPending ? <FeedSkeleton /> : posts.isError && !items.length ? <div className="feed-empty" role="alert"><h3>Couldn’t load posts.</h3><p>Check your connection and try again.</p><Button onClick={() => posts.refetch()}>Try again<ArrowRight size={18} /></Button></div> : items.length ? <><div className="post-grid">{items.map(item => <PostCard key={item.id} post={item} href={url({ post: item.id })} />)}</div><div className="feed-pagination"><p aria-live="polite">Showing {items.length} of {total} posts</p>{posts.isFetchNextPageError && <p role="alert" className="form-error">We couldn’t load more posts. Please try again.</p>}{posts.hasNextPage && <Button variant="secondary" disabled={posts.isFetchingNextPage} onClick={() => posts.fetchNextPage()}>{posts.isFetchingNextPage ? "Loading more…" : posts.isFetchNextPageError ? "Retry loading more" : "More from campus"}<ArrowDown size={17} /></Button>}</div>{posts.isFetchingNextPage && <FeedSkeleton />}</> : <div className="feed-empty"><h3>{filtered ? "No matches yet." : type === "OFFER" ? "Be the first to offer." : "What do you need?"}</h3><p>{filtered ? "Try another search or category." : "The campus marketplace starts with you."}</p><div>{filtered && <Button variant="secondary" onClick={() => filter({ q: "", category: "" })}>Clear filters</Button>}<Button onClick={() => post(type)}>{type === "OFFER" ? "Post an offer" : "Post a request"}<ArrowRight size={18} /></Button></div></div>}
      </section>
      <HowItWorks />
    </main>
    <SiteFooter />
    <button className="mobile-post" onClick={() => post(null)}><Plus size={21} aria-hidden="true" />Post Item</button>
    {detail && <DetailPanel key={detail} id={detail} onClose={() => router.push(url({ post: "" }), { scroll: false })} />}
  </>;
}
