"use client";
import { Asterisk, Menu, ChevronDown, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";
import GhostIconButton from "./GhostIconButton";

export default function Header({
  createNewChat,
  sidebarCollapsed,
  setSidebarOpen,
  selectedModel,
  onModelChange,
}) {
  const [selectedBot, setSelectedBot] = useState(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

  useEffect(() => {
    fetchModels();
  }, []);

  useEffect(() => {
    // Update selected bot when selectedModel prop changes
    if (selectedModel && models.length > 0) {
      const modelExists = models.find((m) => m.name === selectedModel);
      if (modelExists && selectedBot !== selectedModel) {
        setSelectedBot(selectedModel);
      }
    } else if (models.length > 0 && !selectedBot && !selectedModel) {
      // Set default model on first load
      const defaultModel = models[0]?.name || null;
      if (defaultModel) {
        setSelectedBot(defaultModel);
        if (onModelChange) {
          onModelChange(defaultModel);
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [models, selectedModel]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (isDropdownOpen && !event.target.closest('.model-dropdown-container')) {
        setIsDropdownOpen(false);
      }
    };

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isDropdownOpen]);

  const fetchModels = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${API_BASE_URL}/api/models`);
      
      if (!response.ok) {
        throw new Error("Failed to fetch models");
      }

      const data = await response.json();
      setModels(data.models || []);
      
      // Set default model if none selected
      if (data.models && data.models.length > 0 && !selectedBot) {
        const defaultModel = data.default_model || data.models[0].name;
        setSelectedBot(defaultModel);
        if (onModelChange) {
          onModelChange(defaultModel);
        }
      }
    } catch (err) {
      console.error("Error fetching models:", err);
      setError("Failed to load models");
      // Fallback to empty array
      setModels([]);
    } finally {
      setLoading(false);
    }
  };

  const handleModelSelect = (modelName) => {
    setSelectedBot(modelName);
    setIsDropdownOpen(false);
    if (onModelChange) {
      onModelChange(modelName);
    }
  };

  const getModelIcon = (modelName) => {
    // Simple icon based on model name
    if (modelName.toLowerCase().includes("mistral")) return "🌪️";
    if (modelName.toLowerCase().includes("llama")) return "🦙";
    if (modelName.toLowerCase().includes("phi")) return "Φ";
    if (modelName.toLowerCase().includes("gemma")) return "💎";
    return "🤖";
  };

  return (
    <div className="sticky top-0 z-30 flex items-center gap-2 border-b border-zinc-200/60 bg-white/80 px-4 py-3 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/70">
      {sidebarCollapsed && (
        <button
          onClick={() => setSidebarOpen(true)}
          className="md:hidden inline-flex items-center justify-center rounded-lg p-2 hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:hover:bg-zinc-800"
          aria-label="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>
      )}

      <div className="hidden md:flex relative model-dropdown-container">
        <button
          onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          disabled={loading || models.length === 0}
          className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-3 py-2 text-sm font-semibold tracking-tight hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-zinc-800 dark:bg-zinc-950 dark:hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Loading...</span>
            </>
          ) : error || models.length === 0 ? (
            <>
              <Asterisk className="h-4 w-4" />
              <span>No models</span>
            </>
          ) : (
            <>
              <span className="text-sm">
                {getModelIcon(selectedBot || "")}
              </span>
              <span className="max-w-[200px] truncate">
                {selectedBot || "Select model"}
              </span>
            </>
          )}
          <ChevronDown className="h-4 w-4" />
        </button>

        {isDropdownOpen && !loading && models.length > 0 && (
          <div className="absolute top-full left-0 mt-1 w-64 max-h-96 overflow-y-auto rounded-lg border border-zinc-200 bg-white shadow-lg dark:border-zinc-800 dark:bg-zinc-950 z-50">
            {models.map((model) => (
              <button
                key={model.name}
                onClick={() => handleModelSelect(model.name)}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-zinc-100 dark:hover:bg-zinc-800 first:rounded-t-lg last:rounded-b-lg ${
                  selectedBot === model.name
                    ? "bg-zinc-100 dark:bg-zinc-800"
                    : ""
                }`}
              >
                <span className="text-sm">{getModelIcon(model.name)}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{model.name}</div>
                  {model.size && (
                    <div className="text-xs text-zinc-500 dark:text-zinc-400">
                      {(model.size / 1024 / 1024 / 1024).toFixed(2)} GB
                    </div>
                  )}
                </div>
                {selectedBot === model.name && (
                  <span className="text-blue-500">✓</span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="ml-auto flex items-center gap-2"></div>
    </div>
  );
}
