"use client";
import { motion, AnimatePresence } from "framer-motion";
import { X, FileText } from "lucide-react";
import { useState, useEffect } from "react";

export default function UploadMetadataModal({
  isOpen,
  onClose,
  onUpload,
  fileName,
  uploading = false,
}) {
  const [company, setCompany] = useState("");
  const [period, setPeriod] = useState("");

  // Reset form when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setCompany("");
      setPeriod("");
    }
  }, [isOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onUpload({
      company: company.trim() || null,
      period: period.trim() || null,
    });
  };

  const handleCancel = () => {
    setCompany("");
    setPeriod("");
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60"
            onClick={handleCancel}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-900"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Upload PDF</h2>
              <button
                onClick={handleCancel}
                disabled={uploading}
                className="rounded-lg p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mb-4 flex items-center gap-3 rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800/50">
              <FileText className="h-5 w-5 text-zinc-500 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
                  {fileName}
                </div>
                <div className="text-xs text-zinc-500 dark:text-zinc-400">
                  Ready to upload
                </div>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="company"
                  className="block text-sm font-medium mb-2 text-zinc-700 dark:text-zinc-300"
                >
                  Company Name <span className="text-zinc-400">(optional)</span>
                </label>
                <input
                  id="company"
                  type="text"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="E.g. Acme Corp, TechCorp Inc"
                  disabled={uploading}
                  className="w-full rounded-lg border border-zinc-300 px-4 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  autoFocus
                />
                <p className="mt-1.5 text-xs text-zinc-500 dark:text-zinc-400">
                  Leave empty to auto-detect from document
                </p>
              </div>

              <div>
                <label
                  htmlFor="period"
                  className="block text-sm font-medium mb-2 text-zinc-700 dark:text-zinc-300"
                >
                  Period <span className="text-zinc-400">(optional)</span>
                </label>
                <input
                  id="period"
                  type="text"
                  value={period}
                  onChange={(e) => setPeriod(e.target.value)}
                  placeholder="E.g. 2024Q3, 2024Q4, FY2024"
                  disabled={uploading}
                  className="w-full rounded-lg border border-zinc-300 px-4 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <p className="mt-1.5 text-xs text-zinc-500 dark:text-zinc-400">
                  Leave empty to auto-detect from document
                </p>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleCancel}
                  disabled={uploading}
                  className="flex-1 rounded-lg border border-zinc-300 px-4 py-2.5 text-sm font-medium hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="flex-1 rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-100"
                >
                  {uploading ? "Uploading..." : "Upload"}
                </button>
              </div>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

