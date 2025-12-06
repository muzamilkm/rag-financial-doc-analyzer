"use client";

import { useState, forwardRef, useImperativeHandle, useRef } from "react";
import { Pencil, RefreshCw, Check, X, Square } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Message from "./Message";
import Composer from "./Composer";
import { cls, timeAgo } from "./utils";

function ThinkingMessage({ onPause }) {
  return (
    <Message role="assistant">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1">
          <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 [animation-delay:-0.3s]"></div>
          <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 [animation-delay:-0.15s]"></div>
          <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400"></div>
        </div>
        <span className="text-sm text-zinc-500">AI is thinking...</span>
        <button
          onClick={onPause}
          className="ml-auto inline-flex items-center gap-1 rounded-full border border-zinc-300 px-2 py-1 text-xs text-zinc-600 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800"
        >
          <Square className="h-3 w-3" /> Pause
        </button>
      </div>
    </Message>
  );
}

const ChatPane = forwardRef(function ChatPane(
  {
    conversation,
    onSend,
    onEditMessage,
    onResendMessage,
    isThinking,
    onPauseThinking,
  },
  ref
) {
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const composerRef = useRef(null);

  useImperativeHandle(
    ref,
    () => ({
      insertTemplate: (templateContent) => {
        composerRef.current?.insertTemplate(templateContent);
      },
    }),
    []
  );

  if (!conversation) return null;

  const messages = Array.isArray(conversation.messages)
    ? conversation.messages
    : [];
  const count = messages.length || conversation.messageCount || 0;

  function startEdit(m) {
    setEditingId(m.id);
    setDraft(m.content);
  }
  function cancelEdit() {
    setEditingId(null);
    setDraft("");
  }
  function saveEdit() {
    if (!editingId) return;
    onEditMessage?.(editingId, draft);
    cancelEdit();
  }
  function saveAndResend() {
    if (!editingId) return;
    onEditMessage?.(editingId, draft);
    onResendMessage?.(editingId);
    cancelEdit();
  }

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col">
      <div className="flex-1 space-y-5 overflow-y-auto px-4 py-6 sm:px-8">
        <div className="mb-2 text-3xl font-serif tracking-tight sm:text-4xl md:text-5xl">
          <span className="block leading-[1.05] font-sans text-2xl">
            {conversation.title}
          </span>
        </div>
        <div className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
          Updated {timeAgo(conversation.updatedAt)} · {count} messages
        </div>

        {messages.length === 0 ? (
          <div className="rounded-xl border border-dashed border-zinc-300 p-6 text-sm text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">
            No messages yet. Say hello to start.
          </div>
        ) : (
          <>
            {messages.map((m) => (
              <div key={m.id} className="space-y-2">
                {editingId === m.id ? (
                  <div
                    className={cls(
                      "rounded-2xl border p-2",
                      "border-zinc-200 dark:border-zinc-800"
                    )}
                  >
                    <textarea
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      className="w-full resize-y rounded-xl bg-transparent p-2 text-sm outline-none"
                      rows={3}
                    />
                    <div className="mt-2 flex items-center gap-2">
                      <button
                        onClick={saveEdit}
                        className="inline-flex items-center gap-1 rounded-full bg-zinc-900 px-3 py-1.5 text-xs text-white dark:bg-white dark:text-zinc-900"
                      >
                        <Check className="h-3.5 w-3.5" /> Save
                      </button>
                      <button
                        onClick={saveAndResend}
                        className="inline-flex items-center gap-1 rounded-full border px-3 py-1.5 text-xs"
                      >
                        <RefreshCw className="h-3.5 w-3.5" /> Save & Resend
                      </button>
                      <button
                        onClick={cancelEdit}
                        className="inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-xs"
                      >
                        <X className="h-3.5 w-3.5" /> Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <Message role={m.role}>
                    {m.role === "assistant" ? (
                      <div className="markdown-content">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({ children }) => <p className="my-2">{children}</p>,
                            h1: ({ children }) => <h1 className="text-xl font-bold mt-4 mb-2">{children}</h1>,
                            h2: ({ children }) => <h2 className="text-lg font-bold mt-4 mb-2">{children}</h2>,
                            h3: ({ children }) => <h3 className="text-base font-semibold mt-3 mb-2">{children}</h3>,
                            ul: ({ children }) => <ul className="list-disc list-inside my-2 space-y-1">{children}</ul>,
                            ol: ({ children }) => <ol className="list-decimal list-inside my-2 space-y-1">{children}</ol>,
                            li: ({ children }) => <li className="ml-4">{children}</li>,
                            strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                            em: ({ children }) => <em className="italic">{children}</em>,
                            code: ({ children, className }) => {
                              const isInline = !className;
                              return isInline ? (
                                <code className="bg-zinc-100 dark:bg-zinc-800 px-1 py-0.5 rounded text-sm font-mono">{children}</code>
                              ) : (
                                <code className={className}>{children}</code>
                              );
                            },
                            pre: ({ children }) => (
                              <pre className="bg-zinc-100 dark:bg-zinc-800 p-3 rounded-lg overflow-x-auto my-2">
                                {children}
                              </pre>
                            ),
                            hr: () => <hr className="my-4 border-zinc-300 dark:border-zinc-700" />,
                            blockquote: ({ children }) => (
                              <blockquote className="border-l-4 border-zinc-300 dark:border-zinc-700 pl-4 my-2 italic">
                                {children}
                              </blockquote>
                            ),
                            a: ({ href, children }) => (
                              <a href={href} className="text-blue-600 dark:text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">
                                {children}
                              </a>
                            ),
                          }}
                        >
                          {m.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <div className="whitespace-pre-wrap">{m.content}</div>
                    )}
                    {m.role === "user" && (
                      <div className="mt-1 flex gap-2 text-[11px] text-zinc-500">
                        <button
                          className="inline-flex items-center gap-1 hover:underline"
                          onClick={() => startEdit(m)}
                        >
                          <Pencil className="h-3.5 w-3.5" /> Edit
                        </button>
                        <button
                          className="inline-flex items-center gap-1 hover:underline"
                          onClick={() => onResendMessage?.(m.id)}
                        >
                          <RefreshCw className="h-3.5 w-3.5" /> Resend
                        </button>
                      </div>
                    )}
                  </Message>
                )}
              </div>
            ))}
            {isThinking && <ThinkingMessage onPause={onPauseThinking} />}
          </>
        )}
      </div>

      <Composer
        ref={composerRef}
        onSend={async (text) => {
          if (!text.trim()) return;
          setBusy(true);
          await onSend?.(text);
          setBusy(false);
        }}
        busy={busy}
      />
    </div>
  );
});

export default ChatPane;
