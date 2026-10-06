"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  CheckCheck,
  ExternalLink,
  Lock,
  MessageSquare,
  Send,
  Sparkles,
  XCircle,
} from "lucide-react";

import { api, errorMessage } from "@/lib/api/client";
import { SessionBoundary } from "@/lib/auth/session";
import type {
  Conversation,
  ConversationListResponse,
  Message,
  User,
} from "@/lib/api/types";
import { Avatar, Button, Skeleton } from "@/components/ui";
import { SiteFooter, SiteHeader } from "@/components/marketplace/site-header";
import { relativeTime } from "@/features/marketplace/presentation";
import "./messaging.css";

function MessageBubble({
  message,
  isMine,
}: {
  message: Message;
  isMine: boolean;
}) {
  return (
    <div className={`chat-bubble-row ${isMine ? "is-mine" : "is-theirs"}`}>
      <div className={`chat-bubble ${isMine ? "is-mine" : "is-theirs"}`}>
        {message.content}
      </div>
      <div className="chat-bubble-meta">
        <span>{relativeTime(message.created_at)}</span>
        {isMine && (
          <span className="chat-receipt-icon">
            {message.read_at ? (
              <CheckCheck
                size={13}
                className="chat-receipt-read"
                aria-label="Read"
              />
            ) : (
              <Check size={13} aria-label="Sent" />
            )}
          </span>
        )}
      </div>
    </div>
  );
}

function ActiveThread({
  conversationId,
  currentUser,
}: {
  conversationId: string;
  currentUser: User;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [inputText, setInputText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Poll conversation metadata every 8 seconds
  const convQuery = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: ({ signal }) =>
      api<Conversation>(`conversations/${conversationId}`, { signal }),
    refetchInterval: 8000,
    refetchIntervalInBackground: false,
  });

  // Poll messages every 3.5 seconds while open
  const messagesQuery = useQuery({
    queryKey: ["messages", conversationId],
    queryFn: async ({ signal }) => {
      const data = await api<Message[]>(
        `conversations/${conversationId}/messages`,
        { signal }
      );
      // Invalidate conversation list unread count when messages arrive and are marked read
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      return data;
    },
    refetchInterval: 3500,
    refetchIntervalInBackground: false,
  });

  const sendMutation = useMutation({
    mutationFn: (content: string) =>
      api<Message>(`conversations/${conversationId}/messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      }),
    onSuccess: (newMsg) => {
      setInputText("");
      queryClient.setQueryData<Message[]>(
        ["messages", conversationId],
        (old) => (old ? [...old, newMsg] : [newMsg])
      );
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const closeMutation = useMutation({
    mutationFn: () =>
      api<Conversation>(`conversations/${conversationId}/close`, {
        method: "POST",
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["conversation", conversationId], updated);
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messagesQuery.data?.length]);

  const conversation = convQuery.data;
  const messages = messagesQuery.data ?? [];
  const isClosed = Boolean(conversation?.closed_at);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = inputText.trim();
    if (!trimmed || isClosed || sendMutation.isPending) return;
    sendMutation.mutate(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  };

  if (convQuery.isPending) {
    return (
      <div style={{ padding: "32px", display: "flex", flexDirection: "column", gap: "16px" }}>
        <Skeleton />
        <Skeleton />
        <Skeleton />
      </div>
    );
  }

  if (convQuery.isError) {
    return (
      <div style={{ padding: "32px", textAlign: "center" }}>
        <p style={{ color: "var(--destructive)", marginBottom: "16px" }}>
          {errorMessage(convQuery.error)}
        </p>
        <Button onClick={() => convQuery.refetch()}>Try again</Button>
      </div>
    );
  }

  if (!conversation) return null;

  return (
    <div className="messenger-thread">
      {/* Thread Header */}
      <div className="messenger-thread-header">
        <div className="messenger-user-meta">
          <button
            type="button"
            className="md:hidden text-action"
            style={{ padding: "6px", marginInlineEnd: "2px", display: "inline-flex", alignItems: "center" }}
            onClick={() => router.push("/messages")}
            aria-label="Back to messages list"
          >
            <ArrowLeft size={20} />
          </button>
          <Avatar name={conversation.other_participant.name} size="md" />
          <div style={{ minWidth: 0 }}>
            <h2 className="messenger-user-name">
              {conversation.other_participant.name}
            </h2>
            <span className="messenger-user-badge">
              <span className="messenger-user-badge-dot" />
              Verified Ramaiah Student
            </span>
          </div>
        </div>

        <div>
          {!isClosed && (
            <Button
              variant="secondary"
              size="sm"
              disabled={closeMutation.isPending}
              onClick={() => {
                if (
                  confirm(
                    "Close this conversation? Neither participant will be able to send new messages."
                  )
                ) {
                  closeMutation.mutate();
                }
              }}
            >
              <XCircle size={14} /> Close enquiry
            </Button>
          )}
        </div>
      </div>

      {/* Listing Context Banner (Clean Typography & Link — No Broken Image) */}
      <div className="messenger-listing-banner">
        <div className="messenger-listing-info">
          <span
            className={`messenger-listing-tag ${
              conversation.post_type === "OFFER" ? "offer" : "request"
            }`}
          >
            {conversation.post_type === "OFFER" ? "Offering" : "Request"}
          </span>
          <span className="messenger-listing-title">
            {conversation.post_title}
          </span>
          {conversation.post?.price !== undefined &&
            conversation.post?.price !== null && (
              <span className="messenger-listing-price">
                ₹{conversation.post.price} {conversation.post.price_unit ?? ""}
              </span>
            )}
        </div>

        <Link
          href={`/?post=${conversation.post_id}`}
          className="messenger-listing-action"
          target="_blank"
        >
          View listing <ExternalLink size={12} />
        </Link>
      </div>

      {/* Messages Stream */}
      <div className="messenger-stream">
        {messagesQuery.isPending ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <Skeleton />
            <Skeleton />
            <Skeleton />
          </div>
        ) : messages.length === 0 ? (
          <div className="messenger-stream-empty">
            <div className="messenger-empty-icon-wrap">
              <Sparkles size={24} />
            </div>
            <strong style={{ fontSize: "15px", color: "#1c1813" }}>
              Start the conversation
            </strong>
            <p style={{ fontSize: "13px", margin: 0, lineHeight: 1.5 }}>
              Ask about availability, arrange a convenient spot on the MSRIT
              campus, or discuss item details.
            </p>
            <div className="messenger-icebreaker-box">
              💬 <em>&ldquo;Hi {conversation.other_participant.name}, is this still available? Can we meet near the campus library?&rdquo;</em>
            </div>
          </div>
        ) : (
          messages.map((m) => (
            <MessageBubble
              key={m.id}
              message={m}
              isMine={m.sender_id === currentUser.id}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Closed State Banner */}
      {isClosed && (
        <div className="messenger-closed-banner" role="status">
          <Lock size={15} />
          <span>This conversation has been closed. Messages are now read-only.</span>
        </div>
      )}

      {/* Message Composer */}
      {!isClosed && (
        <form onSubmit={handleSend} className="messenger-composer">
          <div className="messenger-composer-input-wrap">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Write a message… (Press Enter to send, Shift + Enter for new line)"
              rows={2}
              maxLength={2000}
              className="messenger-textarea"
            />
            {inputText.length > 1800 && (
              <span className="messenger-char-count">
                {2000 - inputText.length} left
              </span>
            )}
          </div>
          <button
            type="submit"
            className="messenger-send-btn"
            disabled={!inputText.trim() || sendMutation.isPending}
            aria-label="Send message"
          >
            <Send size={18} />
          </button>
        </form>
      )}

      {sendMutation.isError && (
        <div
          role="alert"
          style={{
            padding: "8px 20px",
            background: "var(--destructive-soft)",
            color: "var(--destructive)",
            fontSize: "12px",
            borderTop: "1px solid rgba(167, 47, 43, 0.2)",
          }}
        >
          {errorMessage(sendMutation.error)}
        </div>
      )}
    </div>
  );
}

export function MessagingView({ activeId }: { activeId?: string }) {
  const router = useRouter();

  const convListQuery = useQuery({
    queryKey: ["conversations"],
    queryFn: ({ signal }) =>
      api<ConversationListResponse>("conversations", { signal }),
    refetchInterval: 10000,
  });

  return (
    <SessionBoundary next={activeId ? `/messages/${activeId}` : "/messages"}>
      {(currentUser) => {
        const conversations = convListQuery.data?.items ?? [];

        return (
          <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--background)" }}>
            <SiteHeader />

            <main id="main" className="rm-container messenger-wrapper">
              <div className="messenger-card">
                {/* Left panel: Conversation List */}
                <aside
                  className={`messenger-sidebar ${
                    activeId ? "is-hidden-mobile" : ""
                  }`}
                >
                  <div className="messenger-sidebar-header">
                    <div>
                      <h1 className="messenger-sidebar-title">Messages</h1>
                      <span className="messenger-sidebar-subtitle">
                        Campus enquiries &amp; trades
                      </span>
                    </div>
                    {conversations.length > 0 && (
                      <span className="messenger-badge-total">
                        {conversations.length} {conversations.length === 1 ? "thread" : "threads"}
                      </span>
                    )}
                  </div>

                  <div className="messenger-list-scroll">
                    {convListQuery.isPending ? (
                      <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
                        <Skeleton />
                        <Skeleton />
                        <Skeleton />
                      </div>
                    ) : conversations.length === 0 ? (
                      <div className="messenger-sidebar-empty">
                        <div className="messenger-empty-icon-wrap">
                          <MessageSquare size={26} />
                        </div>
                        <strong style={{ fontSize: "14.5px", color: "#1c1813" }}>
                          No conversations yet
                        </strong>
                        <p style={{ fontSize: "12.5px", margin: 0, lineHeight: 1.5 }}>
                          Reach out to a fellow student on any marketplace listing to begin an enquiry.
                        </p>
                        <Link
                          href="/#recent"
                          className="rm-button rm-button--secondary rm-button--sm"
                          style={{ marginTop: "12px" }}
                        >
                          Explore campus listings
                        </Link>
                      </div>
                    ) : (
                      conversations.map((conv) => {
                        const isSelected = conv.id === activeId;
                        return (
                          <button
                            key={conv.id}
                            type="button"
                            onClick={() => router.push(`/messages/${conv.id}`)}
                            className={`messenger-list-item ${
                              isSelected ? "is-active" : ""
                            }`}
                          >
                            <div className="messenger-item-avatar-wrap">
                              <Avatar name={conv.other_participant.name} size="md" />
                            </div>
                            <div className="messenger-item-content">
                              <div className="messenger-item-top">
                                <strong className="messenger-item-name">
                                  {conv.other_participant.name}
                                </strong>
                                <span className="messenger-item-time">
                                  {relativeTime(conv.last_message_at || conv.created_at)}
                                </span>
                              </div>
                              <div className="messenger-item-sub">
                                <span className="messenger-item-post-title">
                                  📌 {conv.post_title}
                                </span>
                                {conv.unread_count > 0 && (
                                  <span className="messenger-item-unread">
                                    {conv.unread_count}
                                  </span>
                                )}
                              </div>
                            </div>
                          </button>
                        );
                      })
                    )}
                  </div>
                </aside>

                {/* Right panel: Active Thread or Empty Selection */}
                <section
                  className={`messenger-thread ${
                    !activeId ? "is-hidden-mobile" : ""
                  }`}
                >
                  {activeId ? (
                    <ActiveThread
                      conversationId={activeId}
                      currentUser={currentUser}
                    />
                  ) : (
                    <div className="messenger-empty-selection">
                      <div className="messenger-empty-selection-icon">
                        <MessageSquare size={34} />
                      </div>
                      <h2>Select an enquiry</h2>
                      <p>
                        Choose a conversation from the left to read messages and
                        coordinate with verified students on campus.
                      </p>
                    </div>
                  )}
                </section>
              </div>
            </main>

            <SiteFooter />
          </div>
        );
      }}
    </SessionBoundary>
  );
}
