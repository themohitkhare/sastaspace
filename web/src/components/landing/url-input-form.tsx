"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import NextImage from "next/image";
import { Globe } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { validateUrl, extractDomain } from "@/lib/url-utils";
import { trackEvent } from "@/lib/analytics";
import type { RedesignTier, ModelProvider } from "@/hooks/use-redesign";

interface UrlInputFormProps {
  onSubmit: (url: string, tier: RedesignTier, modelProvider: ModelProvider, prompt: string) => void;
  isConnecting?: boolean;
}

export function UrlInputForm({ onSubmit, isConnecting }: UrlInputFormProps) {
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [faviconUrl, setFaviconUrl] = useState<string | null>(null);
  const [tier, setTier] = useState<RedesignTier>("free");
  // Model selection handled by per-step routing on the backend
  const modelProvider: ModelProvider = "gemini";
  const [prompt, setPrompt] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Pre-select Studio tier if tier=studio is in the URL.
  // The pricing page links to /#url-input?tier=studio, so the param lives
  // inside the hash fragment, not in window.location.search.
  useEffect(() => {
    // Check query string first (standard ?tier=studio)
    let tierParam = new URLSearchParams(window.location.search).get("tier");
    // Fall back to hash fragment (/#url-input?tier=studio)
    if (!tierParam && window.location.hash.includes("?")) {
      const hashQuery = window.location.hash.substring(window.location.hash.indexOf("?"));
      tierParam = new URLSearchParams(hashQuery).get("tier");
    }
    if (tierParam === "studio") {
      setTier("premium");
    }
  }, []);

  // Auto-focus URL input on page load
  useEffect(() => {
    const timer = setTimeout(() => {
      inputRef.current?.focus();
    }, 300);
    return () => clearTimeout(timer);
  }, []);

  const fetchFavicon = useCallback((value: string) => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (!value.trim()) {
      setFaviconUrl(null);
      return;
    }

    debounceRef.current = setTimeout(() => {
      const domain = extractDomain(value);
      if (!domain || !domain.includes(".")) {
        setFaviconUrl(null);
        return;
      }

      const iconUrl = `https://${domain}/favicon.ico`;
      const img = new Image();
      img.onload = () => setFaviconUrl(iconUrl);
      img.onerror = () => setFaviconUrl(null);
      img.src = iconUrl;
    }, 500);
  }, []);

  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setInput(value);
    setError(null);
    fetchFavicon(value);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const result = validateUrl(input);

    if (!result.valid) {
      setError(result.error ?? "Please enter a valid website address");
      return;
    }

    onSubmit(result.url, tier, modelProvider, prompt);
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="w-full max-w-xl rounded-2xl bg-background/80 backdrop-blur-sm p-4 border border-border/50" style={{ boxShadow: "var(--shadow-md)" }}>
      {/* Tier and model toggles */}
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <div role="radiogroup" aria-label="Redesign tier" className="flex gap-1 p-1 rounded-lg bg-muted w-fit">
          <button
            type="button"
            role="radio"
            aria-checked={tier === "free"}
            aria-label="Express - fast 2 minute redesign"
            onClick={() => { setTier("free"); trackEvent("tier_selected", { tier: "free" }); }}
            className={[
              "px-4 py-2.5 rounded-md text-sm font-medium transition-colors",
              tier === "free"
                ? "bg-accent text-accent-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            Express
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={tier === "premium"}
            aria-label="Studio - premium detailed redesign"
            onClick={() => { setTier("premium"); trackEvent("tier_selected", { tier: "premium" }); }}
            className={[
              "px-4 py-2.5 rounded-md text-sm font-medium transition-colors",
              tier === "premium"
                ? "bg-accent text-accent-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            Studio
          </button>
        </div>
        <span className="text-xs text-muted-foreground">
          {tier === "free" ? "Fast & free (~2 min)" : "Premium quality (~5 min)"}
        </span>

      </div>

      <div className="flex flex-col sm:flex-row gap-2 sm:gap-0 w-full">
        <div className="relative flex-1">
          <Label htmlFor="url-input" className="sr-only">
            Website URL
          </Label>
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground z-10">
            {faviconUrl ? (
              <NextImage
                src={faviconUrl}
                alt=""
                width={20}
                height={20}
                className="w-5 h-5 rounded-sm"
                onError={() => setFaviconUrl(null)}
                unoptimized
              />
            ) : (
              <Globe className="w-5 h-5" />
            )}
          </div>
          <Input
            ref={inputRef}
            id="url-input"
            type="url"
            placeholder="yourwebsite.com"
            value={input}
            onChange={handleInputChange}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                handleSubmit(e as unknown as React.FormEvent);
              }
            }}
            autoComplete="url"
            className="h-12 ps-12 rounded-lg sm:rounded-r-none text-base font-sans"
            aria-invalid={!!error}
            aria-describedby={error ? "url-error" : undefined}
          />
        </div>
        <Button
          type="submit"
          size="lg"
          disabled={isConnecting}
          className={[
            "h-12 min-h-12 rounded-lg sm:rounded-l-none px-8 bg-accent text-accent-foreground hover:bg-accent/90 font-medium",
            isConnecting ? "animate-pulse" : "",
          ].join(" ")}
        >
          {isConnecting ? "Connecting..." : "Redesign My Site"}
        </Button>
      </div>
      <div className="mt-3">
        <Label htmlFor="prompt-input" className="text-xs text-muted-foreground mb-1 block">
          Custom instructions (optional)
        </Label>
        <textarea
          id="prompt-input"
          rows={2}
          placeholder="e.g., Make it minimal and dark, focus on conversions, use blue as primary color..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          className="w-full rounded-lg border border-border/50 bg-background px-3 py-2 text-sm font-sans text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-y min-h-[2.5rem]"
        />
      </div>
      {error && <p id="url-error" className="text-sm text-destructive mt-2" role="alert">{error}</p>}
      <p className="text-xs text-muted-foreground text-center mt-2">
        Free tier: 3 redesigns per hour
      </p>
    </form>
  );
}
