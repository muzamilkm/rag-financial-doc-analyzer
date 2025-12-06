"use client";

import {
  useRef,
  useState,
  forwardRef,
  useImperativeHandle,
  useEffect,
} from "react";
import { Send, Loader2, Upload } from "lucide-react";
import { cls } from "./utils";

const Composer = forwardRef(function Composer({ onSend, busy }, ref) {
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);
  const [lineCount, setLineCount] = useState(1);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

  useEffect(() => {
    if (inputRef.current) {
      const textarea = inputRef.current;
      const lineHeight = 24;
      const minHeight = 24;

      textarea.style.height = "auto";
      const scrollHeight = textarea.scrollHeight;
      const calculatedLines = Math.max(1, Math.ceil(scrollHeight / lineHeight));

      setLineCount(calculatedLines);

      if (calculatedLines <= 12) {
        textarea.style.height = `${Math.max(minHeight, scrollHeight)}px`;
        textarea.style.overflowY = "hidden";
      } else {
        textarea.style.height = `${12 * lineHeight}px`;
        textarea.style.overflowY = "auto";
      }
    }
  }, [value]);

  useImperativeHandle(
    ref,
    () => ({
      insertTemplate: (templateContent) => {
        setValue((prev) => {
          const newValue = prev
            ? `${prev}\n\n${templateContent}`
            : templateContent;
          setTimeout(() => {
            inputRef.current?.focus();
            const length = newValue.length;
            inputRef.current?.setSelectionRange(length, length);
          }, 0);
          return newValue;
        });
      },
      focus: () => {
        inputRef.current?.focus();
      },
    }),
    []
  );

  async function handleSend() {
    if (!value.trim() || sending) return;
    setSending(true);
    try {
      await onSend?.(value);
      setValue("");
      inputRef.current?.focus();
    } finally {
      setSending(false);
    }
  }

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.type !== "application/pdf") {
      alert("Please select a PDF file only.");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE_URL}/api/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || "Upload failed");
      }

      // Success
      alert(
        `✅ PDF uploaded successfully!\n\n` +
          `File: ${data.statistics.filename}\n` +
          `Company: ${data.statistics.company}\n` +
          `Period: ${data.statistics.period}\n` +
          `Text chunks: ${data.statistics.text_chunks}\n` +
          `Table chunks: ${data.statistics.table_chunks}\n` +
          `Total: ${data.statistics.total_chunks} chunks ingested`
      );
    } catch (error) {
      console.error("PDF upload error:", error);
      alert(`❌ Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const hasContent = value.trim().length > 0;

  return (
    <div className="border-t border-zinc-200/60 p-4 dark:border-zinc-800">
      <div
        className={cls(
          "mx-auto flex flex-col rounded-3xl border bg-white shadow-sm dark:bg-zinc-950 transition-all duration-200",
          "max-w-3xl border-zinc-200 dark:border-zinc-800"
        )}
      >
        {/* Textarea area - grows upward */}
        <div className="flex-1 px-4 pt-4 pb-2">
          <textarea
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Analyze financial reports, ask about metrics, trends..."
            rows={1}
            className={cls(
              "w-full resize-none bg-transparent text-sm outline-none placeholder:text-zinc-400 transition-all duration-200",
              "min-h-[24px] text-left leading-6"
            )}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
        </div>

        {/* Bottom toolbar: upload on left, send on right */}
        <div className="flex items-center justify-between px-3 pb-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            className="hidden"
            id="pdf-upload"
          />
          <label htmlFor="pdf-upload">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="inline-flex shrink-0 items-center justify-center rounded-full p-2 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={uploading ? "Uploading..." : "Upload PDF"}
            >
              {uploading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Upload className="h-5 w-5" />
              )}
            </button>
          </label>

          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={handleSend}
              disabled={sending || busy || !hasContent}
              className={cls(
                "inline-flex shrink-0 items-center justify-center rounded-full p-2.5 transition-colors",
                hasContent
                  ? "bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
                  : "bg-zinc-200 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-600 cursor-not-allowed"
              )}
            >
              {sending || busy ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto mt-2 max-w-3xl px-1 text-center text-[11px] text-zinc-400 dark:text-zinc-500">
        Always verify financial data and insights with authoritative sources.
      </div>
    </div>
  );
});

export default Composer;
