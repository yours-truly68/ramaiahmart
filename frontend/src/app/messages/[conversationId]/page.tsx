import { MessagingView } from "@/features/messaging/messaging-view";

export const metadata = {
  title: "Conversation — RamaiahMart",
  description: "Campus direct messages and enquiries on RamaiahMart.",
};

export default async function ConversationPage({
  params,
}: {
  params: Promise<{ conversationId: string }>;
}) {
  const { conversationId } = await params;
  return <MessagingView activeId={conversationId} />;
}
