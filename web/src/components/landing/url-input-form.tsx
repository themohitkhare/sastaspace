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
  onSubmit: (url: string, tier: RedesignTier, modelProvider: ModelProvider) => void;
  isConnecting?: boolean;
}

export function UrlInputForm({ onSubmit, isConnecting }: UrlInputFormProps) {
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [faviconUrl, setFaviconUrl] = useState<string | null>(null);
  const [tier, setTier] = useState<RedesignTier>("free");
  const [modelProvider, setModelProvider] = useState<ModelProvider>("claude");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Pre-select Studio tier if ?tier=studio is in the URL (from pricing page CTA)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("tier") === "studio") {
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

    onSubmit(result.url, tier, modelProvider);
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

        <div role="radiogroup" aria-label="AI model" className="flex items-center gap-1 p-1 rounded-lg bg-muted w-fit">
          <span className="px-2 text-xs font-medium text-muted-foreground" aria-hidden="true">AI Model</span>
          <button
            type="button"
            role="radio"
            aria-checked={modelProvider === "claude"}
            aria-label="Claude AI model"
            onClick={() => setModelProvider("claude")}
            className={[
              "px-4 py-2.5 rounded-md text-sm font-medium transition-colors",
              modelProvider === "claude"
                ? "bg-accent text-accent-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            Claude
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={modelProvider === "gemini"}
            aria-label="Gemini AI model"
            onClick={() => setModelProvider("gemini")}
            className={[
              "px-4 py-2.5 rounded-md text-sm font-medium transition-colors",
              modelProvider === "gemini"
                ? "bg-accent text-accent-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            Gemini
          </button>
        </div>
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
      {error && <p id="url-error" className="text-sm text-destructive mt-2" role="alert">{error}</p>}
      <p className="text-xs text-muted-foreground text-center mt-2">
        Free tier: 3 redesigns per hour
      </p>
    </form>
  );
}
