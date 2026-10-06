import type { Metadata } from "next";
import { MessagingView } from "@/features/messaging/messaging-view";

export const metadata: Metadata = {
  title: "Messages",
  description: "Campus direct messages and enquiries on RamaiahMart.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function MessagesPage() {
  return <MessagingView />;
}
