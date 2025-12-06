"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";
import ChatPane from "./ChatPane";
import ThemeToggle from "./ThemeToggle";
import {
  INITIAL_CONVERSATIONS,
  INITIAL_TEMPLATES,
  INITIAL_FOLDERS,
} from "./mockData";

export default function AIAssistantUI() {
  const [theme, setTheme] = useState(() => {
    const saved =
      typeof window !== "undefined" && localStorage.getItem("theme");
    if (saved) return saved;
    if (
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    )
      return "dark";
    return "light";
  });

  useEffect(() => {
    try {
      if (theme === "dark") document.documentElement.classList.add("dark");
      else document.documentElement.classList.remove("dark");
      document.documentElement.setAttribute("data-theme", theme);
      document.documentElement.style.colorScheme = theme;
      localStorage.setItem("theme", theme);
    } catch {}
  }, [theme]);

  useEffect(() => {
    try {
      const media =
        window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");
      if (!media) return;
      const listener = (e) => {
        const saved = localStorage.getItem("theme");
        if (!saved) setTheme(e.matches ? "dark" : "light");
      };
      media.addEventListener("change", listener);
      return () => media.removeEventListener("change", listener);
    } catch {}
  }, []);

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    try {
      const raw = localStorage.getItem("sidebar-collapsed");
      return raw ? JSON.parse(raw) : { recent: false };
    } catch {
      return { recent: false };
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem("sidebar-collapsed", JSON.stringify(collapsed));
    } catch {}
  }, [collapsed]);

  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      const saved = localStorage.getItem("sidebar-collapsed-state");
      return saved ? JSON.parse(saved) : false;
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(
        "sidebar-collapsed-state",
        JSON.stringify(sidebarCollapsed)
      );
    } catch {}
  }, [sidebarCollapsed]);

  const [conversations, setConversations] = useState([]);
  const [selectedId, setSelectedId] = useState(null);

  const [query, setQuery] = useState("");
  const searchRef = useRef(null);

  const [isThinking, setIsThinking] = useState(false);
  const [thinkingConvId, setThinkingConvId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedModel, setSelectedModel] = useState(null);

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

  // Fetch all chats on component mount
  useEffect(() => {
    fetchAllChats();
  }, []);

  const fetchAllChats = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/chats`);
      if (!response.ok) throw new Error("Failed to fetch chats");
      const data = await response.json();

      // Transform backend format to frontend format
      const transformedChats = data.chats.map((chat) => ({
        id: chat.chat_id,
        title: chat.title || "New Chat",
        updatedAt: chat.updated_at,
        messageCount: chat.message_count,
        preview: "",
        messages: [],
      }));

      setConversations(transformedChats);
    } catch (error) {
      console.error("Error fetching chats:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchChatMessages = async (chatId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chats/${chatId}`);
      if (!response.ok) throw new Error("Failed to fetch chat messages");
      const data = await response.json();

      // Transform messages
      const transformedMessages = data.messages.map((msg) => ({
        id: msg.id.toString(),
        role: msg.role,
        content: msg.content,
        sources: msg.sources,
        createdAt: msg.created_at,
      }));

      // Update conversation with messages
      setConversations((prev) =>
        prev.map((c) =>
          c.id === chatId
            ? {
                ...c,
                messages: transformedMessages,
                preview:
                  transformedMessages[
                    transformedMessages.length - 1
                  ]?.content?.slice(0, 80) || "",
              }
            : c
        )
      );

      return transformedMessages;
    } catch (error) {
      console.error("Error fetching chat messages:", error);
      return [];
    }
  };

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "n") {
        e.preventDefault();
        createNewChat();
      }
      if (!e.metaKey && !e.ctrlKey && e.key === "/") {
        const tag = document.activeElement?.tagName?.toLowerCase();
        if (tag !== "input" && tag !== "textarea") {
          e.preventDefault();
          searchRef.current?.focus();
        }
      }
      if (e.key === "Escape" && sidebarOpen) setSidebarOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sidebarOpen, conversations]);

  useEffect(() => {
    if (!selectedId && conversations.length > 0) {
      createNewChat();
    }
  }, []);

  const filtered = useMemo(() => {
    if (!query.trim()) return conversations;
    const q = query.toLowerCase();
    return conversations.filter(
      (c) =>
        c.title.toLowerCase().includes(q) || c.preview.toLowerCase().includes(q)
    );
  }, [conversations, query]);

  const recent = filtered
    .sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1))
    .slice(0, 10);

  function createNewChat() {
    // Create a temporary chat locally
    const tempId = "temp_" + Math.random().toString(36).slice(2);
    const item = {
      id: tempId,
      title: "New Chat",
      updatedAt: new Date().toISOString(),
      messageCount: 0,
      preview: "",
      messages: [],
    };
    setConversations((prev) => [item, ...prev]);
    setSelectedId(tempId);
    setSidebarOpen(false);
  }

  async function clearAllData() {
    if (
      confirm(
        "Are you sure you want to clear all chats? This action cannot be undone."
      )
    ) {
      try {
        const response = await fetch(`${API_BASE_URL}/api/chats`, {
          method: "DELETE",
        });

        if (!response.ok) throw new Error("Failed to delete chats");

        setConversations([]);
        setSelectedId(null);
        console.log("All data cleared");
      } catch (error) {
        console.error("Error clearing chats:", error);
        alert("Failed to clear chats. Please try again.");
      }
    }
  }

  async function deleteChat(chatId) {
    if (confirm("Are you sure you want to delete this chat?")) {
      try {
        const response = await fetch(`${API_BASE_URL}/api/chats/${chatId}`, {
          method: "DELETE",
        });

        if (!response.ok) throw new Error("Failed to delete chat");

        setConversations((prev) => prev.filter((c) => c.id !== chatId));
        if (selectedId === chatId) {
          setSelectedId(null);
        }
      } catch (error) {
        console.error("Error deleting chat:", error);
        alert("Failed to delete chat. Please try again.");
      }
    }
  }

  async function sendMessage(convId, content) {
    if (!content.trim()) return;

    const now = new Date().toISOString();
    const userMsg = {
      id: "temp_" + Math.random().toString(36).slice(2),
      role: "user",
      content,
      createdAt: now,
    };

    // Optimistically add user message
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id !== convId) return c;
        const msgs = [...(c.messages || []), userMsg];
        return {
          ...c,
          messages: msgs,
          updatedAt: now,
          messageCount: msgs.length,
          preview: content.slice(0, 80),
        };
      })
    );

    setIsThinking(true);
    setThinkingConvId(convId);

    try {
      // Call backend API
      const chatId = convId.startsWith("temp_") ? null : convId;
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: content,
          chat_id: chatId,
          model: selectedModel, // Include selected model
        }),
      });

      if (!response.ok) throw new Error("Failed to send message");

      const data = await response.json();
      const newChatId = data.chat_id;

      // Add assistant response
      const asstMsg = {
        id: Math.random().toString(36).slice(2),
        role: "assistant",
        content: data.answer,
        sources: data.sources,
        createdAt: new Date().toISOString(),
      };

      setConversations((prev) =>
        prev.map((c) => {
          // Update the correct conversation (handle temp ID replacement)
          if (c.id !== convId && c.id !== newChatId) return c;

          const msgs = [...(c.messages || []), asstMsg];
          return {
            ...c,
            id: newChatId, // Update to real ID if it was temporary
            messages: msgs,
            updatedAt: new Date().toISOString(),
            messageCount: msgs.length,
            preview: asstMsg.content.slice(0, 80),
          };
        })
      );

      // Update selected ID if it was temporary
      if (selectedId === convId && convId.startsWith("temp_")) {
        setSelectedId(newChatId);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      // Remove the optimistic user message on error
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id !== convId) return c;
          return {
            ...c,
            messages: (c.messages || []).filter((m) => m.id !== userMsg.id),
          };
        })
      );
      alert("Failed to send message. Please try again.");
    } finally {
      setIsThinking(false);
      setThinkingConvId(null);
    }
  }

  function editMessage(convId, messageId, newContent) {
    const now = new Date().toISOString();
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id !== convId) return c;
        const msgs = (c.messages || []).map((m) =>
          m.id === messageId ? { ...m, content: newContent, editedAt: now } : m
        );
        return {
          ...c,
          messages: msgs,
          preview: msgs[msgs.length - 1]?.content?.slice(0, 80) || c.preview,
        };
      })
    );
  }

  function resendMessage(convId, messageId) {
    const conv = conversations.find((c) => c.id === convId);
    const msg = conv?.messages?.find((m) => m.id === messageId);
    if (!msg) return;
    sendMessage(convId, msg.content);
  }

  function pauseThinking() {
    setIsThinking(false);
    setThinkingConvId(null);
  }

  const composerRef = useRef(null);

  const selected = conversations.find((c) => c.id === selectedId) || null;

  // Load messages when a chat is selected
  useEffect(() => {
    if (selectedId && !selectedId.startsWith("temp_")) {
      const conv = conversations.find((c) => c.id === selectedId);
      if (conv && (!conv.messages || conv.messages.length === 0)) {
        fetchChatMessages(selectedId);
      }
    }
  }, [selectedId]);

  return (
    <div className="h-screen w-full bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      <div className="md:hidden sticky top-0 z-40 flex items-center gap-2 border-b border-zinc-200/60 bg-white/80 px-3 py-2 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/70">
        <div className="ml-1 flex items-center gap-2 text-sm font-semibold tracking-tight">
          <span className="inline-flex h-4 w-4 items-center justify-center">
            ✱
          </span>{" "}
          Financial Analyzer
        </div>
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle theme={theme} setTheme={setTheme} />
        </div>
      </div>

      <div className="flex h-[calc(100vh-0px)] w-full">
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          theme={theme}
          setTheme={setTheme}
          collapsed={collapsed}
          setCollapsed={setCollapsed}
          sidebarCollapsed={sidebarCollapsed}
          setSidebarCollapsed={setSidebarCollapsed}
          conversations={conversations}
          recent={recent}
          selectedId={selectedId}
          onSelect={(id) => setSelectedId(id)}
          onDeleteChat={deleteChat}
          query={query}
          setQuery={setQuery}
          searchRef={searchRef}
          createNewChat={createNewChat}
          onClearAllData={clearAllData}
        />

        <main className="relative flex min-w-0 flex-1 flex-col">
          <Header
            createNewChat={createNewChat}
            sidebarCollapsed={sidebarCollapsed}
            setSidebarOpen={setSidebarOpen}
            selectedModel={selectedModel}
            onModelChange={setSelectedModel}
          />
          <ChatPane
            ref={composerRef}
            conversation={selected}
            onSend={(content) => selected && sendMessage(selected.id, content)}
            onEditMessage={(messageId, newContent) =>
              selected && editMessage(selected.id, messageId, newContent)
            }
            onResendMessage={(messageId) =>
              selected && resendMessage(selected.id, messageId)
            }
            isThinking={isThinking && thinkingConvId === selected?.id}
            onPauseThinking={pauseThinking}
          />
        </main>
      </div>
    </div>
  );
}
