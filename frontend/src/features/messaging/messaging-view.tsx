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
  MessageSquare,
  Send,
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
import { Avatar, Badge, Button, Skeleton } from "@/components/ui";
import { SiteFooter, SiteHeader } from "@/components/marketplace/site-header";
import { relativeTime } from "@/features/marketplace/presentation";
import { isSafeHttpUrl } from "@/lib/security/url";

function MessageBubble({
  message,
  isMine,
}: {
  message: Message;
  isMine: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: isMine ? "flex-end" : "flex-start",
        marginBottom: "12px",
      }}
    >
      <div
        style={{
          maxWidth: "80%",
          padding: "10px 14px",
          borderRadius: "16px",
          borderTopRightRadius: isMine ? "4px" : "16px",
          borderTopLeftRadius: !isMine ? "4px" : "16px",
          background: isMine ? "var(--foreground)" : "var(--card)",
          color: isMine ? "var(--card)" : "var(--foreground)",
          border: isMine ? "none" : "1px solid var(--border)",
          fontSize: "14px",
          lineHeight: 1.5,
          wordBreak: "break-word",
          whiteSpace: "pre-wrap",
          boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
        }}
      >
        {message.content}
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "4px",
          fontSize: "11px",
          color: "var(--muted-foreground)",
          marginTop: "4px",
          paddingInline: "4px",
        }}
      >
        <span>{relativeTime(message.created_at)}</span>
        {isMine && (
          <span>
            {message.read_at ? (
              <CheckCheck size={13} style={{ color: "var(--accent-orange)" }} aria-label="Read" />
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
        <Skeleton shape="image" />
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
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "var(--card)",
      }}
    >
      {/* Header bar */}
      <div
        style={{
          padding: "14px 20px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
          background: "var(--card)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
          <button
            type="button"
            className="md:hidden text-action"
            style={{ padding: "4px", marginInlineEnd: "4px" }}
            onClick={() => router.push("/messages")}
            aria-label="Back to messages"
          >
            <ArrowLeft size={19} />
          </button>
          <Avatar name={conversation.other_participant.name} size="md" />
          <div style={{ minWidth: 0 }}>
            <h2
              style={{
                fontSize: "15px",
                fontWeight: 700,
                margin: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {conversation.other_participant.name}
            </h2>
            <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>
              Ramaiah student
            </span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {!isClosed && (
            <Button
              variant="secondary"
              size="sm"
              disabled={closeMutation.isPending}
              onClick={() => {
                if (confirm("Close this conversation? Neither participant will be able to send new messages.")) {
                  closeMutation.mutate();
                }
              }}
            >
              <XCircle size={14} /> Close
            </Button>
          )}
        </div>
      </div>

      {/* Listing Context Banner */}
      <div
        style={{
          padding: "12px 20px",
          background: "var(--background)",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "14px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
          {conversation.post_image_url && isSafeHttpUrl(conversation.post_image_url) ? (
            /* Listing image URLs are supplied by API storage */
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={conversation.post_image_url}
              alt={conversation.post_title || "Marketplace listing photo"}
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "6px",
                objectFit: "cover",
                border: "1px solid var(--border)",
              }}
            />
          ) : (
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "6px",
                background: "var(--surface-muted)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--muted-foreground)",
                fontSize: "10px",
                fontWeight: 600,
              }}
            >
              No image
            </div>
          )}
          <div style={{ minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <Badge tone={conversation.post_type === "OFFER" ? "offer" : "request"}>
                {conversation.post_type}
              </Badge>
              <span
                style={{
                  fontSize: "14px",
                  fontWeight: 600,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {conversation.post_title}
              </span>
            </div>
            {conversation.post?.price && (
              <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>
                ₹{conversation.post.price} {conversation.post.price_unit ?? ""}
              </span>
            )}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {/* If post has WhatsApp enabled and author provided link */}
          {conversation.post_type === "OFFER" && (
            <Link
              href={`/?post=${conversation.post_id}`}
              className="text-action"
              style={{ fontSize: "12px", display: "inline-flex", alignItems: "center", gap: "4px" }}
            >
              View listing <ExternalLink size={12} />
            </Link>
          )}
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "20px",
          background: "var(--background)",
        }}
      >
        {messagesQuery.isPending ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <Skeleton />
            <Skeleton />
          </div>
        ) : messages.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "40px 20px",
              color: "var(--muted-foreground)",
            }}
          >
            <MessageSquare size={32} style={{ margin: "0 auto 12px", opacity: 0.4 }} />
            <p style={{ fontSize: "14px", fontWeight: 500, margin: 0 }}>
              No messages yet in this enquiry.
            </p>
            <p style={{ fontSize: "12px", marginTop: "4px" }}>
              Say hello or ask if the item is still available.
            </p>
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
        <div
          role="status"
          style={{
            padding: "12px 20px",
            background: "var(--surface-muted)",
            borderTop: "1px solid var(--border)",
            fontSize: "13px",
            color: "var(--muted-foreground)",
            textAlign: "center",
          }}
        >
          This conversation is closed. Further messages cannot be sent.
        </div>
      )}

      {/* Composer */}
      {!isClosed && (
        <form
          onSubmit={handleSend}
          style={{
            padding: "14px 20px",
            background: "var(--card)",
            borderTop: "1px solid var(--border)",
            display: "flex",
            alignItems: "flex-end",
            gap: "10px",
          }}
        >
          <div style={{ flex: 1, position: "relative" }}>
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message… (Enter to send, Shift+Enter for new line)"
              rows={2}
              maxLength={2000}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: "8px",
                border: "1px solid var(--input-border)",
                background: "var(--background)",
                color: "var(--foreground)",
                fontSize: "14px",
                resize: "none",
                fontFamily: "inherit",
              }}
            />
            {inputText.length > 1800 && (
              <span
                style={{
                  position: "absolute",
                  bottom: "6px",
                  right: "8px",
                  fontSize: "10px",
                  color: "var(--muted-foreground)",
                }}
              >
                {2000 - inputText.length}
              </span>
            )}
          </div>
          <Button
            variant="accent"
            type="submit"
            disabled={!inputText.trim() || sendMutation.isPending}
            style={{ height: "42px", paddingInline: "16px" }}
          >
            <Send size={16} />
            <span className="sr-only">Send</span>
          </Button>
        </form>
      )}
      {sendMutation.isError && (
        <div
          role="alert"
          style={{
            padding: "6px 20px",
            background: "var(--destructive-soft)",
            color: "var(--destructive)",
            fontSize: "12px",
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

            <main
              id="main"
              className="rm-container"
              style={{
                flex: 1,
                paddingBlock: "24px",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: activeId
                    ? "minmax(280px, 340px) 1fr"
                    : "minmax(280px, 340px) 1fr",
                  borderRadius: "12px",
                  border: "1px solid var(--border)",
                  overflow: "hidden",
                  minHeight: "72vh",
                  background: "var(--card)",
                }}
                className="messaging-grid"
              >
                {/* Left panel: Conversation List */}
                <aside
                  style={{
                    borderRight: "1px solid var(--border)",
                    display: activeId ? "none" : "flex",
                    flexDirection: "column",
                    background: "var(--card)",
                  }}
                  className={`conversations-sidebar ${!activeId ? "block-always" : "md:flex"}`}
                >
                  <div
                    style={{
                      padding: "16px 20px",
                      borderBottom: "1px solid var(--border)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <div>
                      <h1 style={{ fontSize: "18px", fontWeight: 700, margin: 0 }}>
                        Messages
                      </h1>
                      <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>
                        Campus enquiries
                      </span>
                    </div>
                  </div>

                  <div style={{ flex: 1, overflowY: "auto" }}>
                    {convListQuery.isPending ? (
                      <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
                        <Skeleton />
                        <Skeleton />
                        <Skeleton />
                      </div>
                    ) : conversations.length === 0 ? (
                      <div
                        style={{
                          padding: "48px 24px",
                          textAlign: "center",
                          color: "var(--muted-foreground)",
                        }}
                      >
                        <MessageSquare size={32} style={{ margin: "0 auto 12px", opacity: 0.3 }} />
                        <p style={{ fontSize: "14px", fontWeight: 600, margin: 0 }}>
                          No messages yet
                        </p>
                        <p style={{ fontSize: "12px", marginTop: "6px" }}>
                          When you message a seller or request an item, your conversations will show up here.
                        </p>
                        <Link
                          href="/#recent"
                          className="rm-button rm-button--secondary rm-button--sm"
                          style={{ marginTop: "16px", display: "inline-block" }}
                        >
                          Browse listings
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
                            style={{
                              width: "100%",
                              padding: "14px 18px",
                              borderBottom: "1px solid var(--border)",
                              display: "flex",
                              alignItems: "center",
                              gap: "12px",
                              textAlign: "left",
                              background: isSelected
                                ? "var(--accent-soft-orange)"
                                : "transparent",
                              cursor: "pointer",
                              borderInline: "none",
                              borderTop: "none",
                              transition: "background 120ms ease",
                            }}
                          >
                            <Avatar name={conv.other_participant.name} size="md" />
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div
                                style={{
                                  display: "flex",
                                  justifyContent: "space-between",
                                  alignItems: "baseline",
                                }}
                              >
                                <strong
                                  style={{
                                    fontSize: "14px",
                                    color: "var(--foreground)",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                  }}
                                >
                                  {conv.other_participant.name}
                                </strong>
                                <span
                                  style={{
                                    fontSize: "11px",
                                    color: "var(--muted-foreground)",
                                    flexShrink: 0,
                                  }}
                                >
                                  {relativeTime(conv.last_message_at || conv.created_at)}
                                </span>
                              </div>
                              <div
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "6px",
                                  marginTop: "3px",
                                }}
                              >
                                <span
                                  style={{
                                    fontSize: "12px",
                                    color: "var(--muted-foreground)",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                  }}
                                >
                                  {conv.post_title}
                                </span>
                              </div>
                            </div>
                            {conv.unread_count > 0 && (
                              <span
                                style={{
                                  background: "var(--accent-orange)",
                                  color: "#ffffff",
                                  fontSize: "11px",
                                  fontWeight: 700,
                                  borderRadius: "999px",
                                  padding: "2px 6px",
                                  minWidth: "18px",
                                  textAlign: "center",
                                }}
                              >
                                {conv.unread_count}
                              </span>
                            )}
                          </button>
                        );
                      })
                    )}
                  </div>
                </aside>

                {/* Right panel: Active Thread or Empty Selection */}
                <section
                  style={{
                    display: !activeId ? "none" : "flex",
                    flexDirection: "column",
                    height: "100%",
                  }}
                  className={`thread-container ${activeId ? "block-always" : "md:flex"}`}
                >
                  {activeId ? (
                    <ActiveThread conversationId={activeId} currentUser={currentUser} />
                  ) : (
                    <div
                      style={{
                        flex: 1,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        padding: "32px",
                        textAlign: "center",
                        color: "var(--muted-foreground)",
                      }}
                    >
                      <MessageSquare size={40} style={{ opacity: 0.3, marginBottom: "16px" }} />
                      <h2 style={{ fontSize: "16px", fontWeight: 600, color: "var(--foreground)", margin: 0 }}>
                        Select a conversation
                      </h2>
                      <p style={{ fontSize: "13px", marginTop: "6px", maxWidth: "36ch" }}>
                        Choose an enquiry from the left to read messages and chat with campus students.
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
