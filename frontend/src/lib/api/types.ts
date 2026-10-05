/** Mirrors backend/app/schemas/{post,category,media,user}.py. */
export type PostType = "OFFER" | "REQUEST";
export type Category = { id: string; name: string; slug: string; is_active: boolean; created_at: string };
export type PostImage = { id: string; post_id: string; storage_key: string; public_url: string | null; position: number; created_at: string };
export type Post = {
  id: string;
  author: { id: string; name: string; university_verified: boolean; profile_image_key: string | null };
  category: Pick<Category, "id" | "name" | "slug">;
  type: PostType;
  status: "DRAFT" | "PENDING_REVIEW" | "PUBLISHED" | "REJECTED" | "ARCHIVED" | "SOLD" | "RENTED" | "CLOSED";
  title: string; description: string; price: string | null; price_unit: string | null;
  created_at: string; updated_at: string; published_at: string | null; images: PostImage[];
};
export type PostPage = { items: Post[]; total: number; page: number; page_size: number; pages: number };
export type User = { id: string; name: string; email: string; university_verified: boolean; profile_image_key: string | null; profile_image_url: string | null; bio: string | null; created_at: string; updated_at: string };

export type AuthConfig = { allowed_email_domains: string[]; password_min_length: number; verification_code_available: boolean; email_delivery_available: boolean };
export type MediaConfig = { max_file_size: number; content_types: string[] };
export type UserPostStats = { listings: number; requests: number; published: number };
