import type { Metadata } from "next";
import { MessagingView } from "@/features/messaging/messaging-view";

export const metadata: Metadata = {
  title: "Conversation",
  description: "Campus direct messages and enquiries on RamaiahMart.",
  robots: {
    index: false,
    follow: false,
  },
};

export default async function ConversationPage({
  params,
}: {
  params: Promise<{ conversationId: string }>;
}) {
  const { conversationId } = await params;
  return <MessagingView activeId={conversationId} />;
}
