import type { Metadata } from "next";
import ProfilePage from "@/features/account/profile-page";

export const metadata: Metadata = {
  title: "Your campus profile",
  description: "Manage your RamaiahMart listings, draft posts, and account settings.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function Page() {
  return <ProfilePage />;
}
