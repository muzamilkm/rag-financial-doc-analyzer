"use client";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, X, FileText } from "lucide-react";
import { cls } from "./utils";

export default function UploadSuccessCard({ statistics, onClose }) {
  if (!statistics) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        className="mx-auto mb-4 max-w-3xl"
      >
        <div
          className={cls(
            "relative rounded-2xl border bg-white p-5 shadow-sm dark:bg-zinc-950",
            "border-green-200 dark:border-green-900/30",
            "bg-green-50/50 dark:bg-green-950/20"
          )}
        >
          <button
            onClick={onClose}
            className="absolute right-3 top-3 rounded-lg p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
          >
            <X className="h-4 w-4" />
          </button>

          <div className="flex items-start gap-4 pr-8">
            <div className="mt-0.5 shrink-0">
              <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>

            <div className="flex-1 min-w-0">
              <h3 className="mb-3 text-base font-semibold text-zinc-900 dark:text-zinc-100">
                PDF Uploaded Successfully
              </h3>

              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <FileText className="h-4 w-4 shrink-0 text-zinc-500" />
                  <span className="font-medium text-zinc-700 dark:text-zinc-300">
                    File:
                  </span>
                  <span className="text-zinc-600 dark:text-zinc-400 truncate">
                    {statistics.filename}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 rounded-lg bg-white/60 p-3 dark:bg-zinc-900/40">
                  <div>
                    <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">
                      Company
                    </div>
                    <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {statistics.company || "Unknown"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">
                      Period
                    </div>
                    <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {statistics.period || "Unknown"}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-6 pt-2 text-sm">
                  <div>
                    <span className="text-zinc-500 dark:text-zinc-400">
                      Text chunks:
                    </span>{" "}
                    <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                      {statistics.text_chunks}
                    </span>
                  </div>
                  <div>
                    <span className="text-zinc-500 dark:text-zinc-400">
                      Table chunks:
                    </span>{" "}
                    <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                      {statistics.table_chunks}
                    </span>
                  </div>
                  <div>
                    <span className="text-zinc-500 dark:text-zinc-400">
                      Total:
                    </span>{" "}
                    <span className="font-semibold text-green-600 dark:text-green-400">
                      {statistics.total_chunks} chunks
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

