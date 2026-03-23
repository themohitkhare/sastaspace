"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import NextImage from "next/image";
import { Globe } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { validateUrl, extractDomain } from "@/lib/url-utils";
import type { RedesignTier, ModelProvider } from "@/hooks/use-redesign";

interface UrlInputFormProps {
  onSubmit: (url: string, tier: RedesignTier, modelProvider: ModelProvider) => void;
}

export function UrlInputForm({ onSubmit }: UrlInputFormProps) {
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [faviconUrl, setFaviconUrl] = useState<string | null>(null);
  const [tier, setTier] = useState<RedesignTier>("free");
  const [modelProvider, setModelProvider] = useState<ModelProvider>("claude");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
    <form onSubmit={handleSubmit} noValidate className="w-full max-w-xl">
      {/* Tier and model toggles */}
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <div className="flex gap-1 p-1 rounded-lg bg-muted w-fit">
          <button
            type="button"
            onClick={() => setTier("free")}
            className={[
              "px-4 py-1.5 rounded-md text-sm font-medium transition-colors",
              tier === "free"
                ? "bg-accent text-accent-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            Express
          </button>
          <button
            type="button"
            onClick={() => setTier("premium")}
            className={[
              "px-4 py-1.5 rounded-md text-sm font-medium transition-colors",
              tier === "premium"
                ? "bg-accent text-accent-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            Studio
          </button>
        </div>

        <div className="flex items-center gap-1 p-1 rounded-lg bg-muted w-fit">
          <span className="px-2 text-xs font-medium text-muted-foreground">AI Model</span>
          <button
            type="button"
            onClick={() => setModelProvider("claude")}
            className={[
              "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
              modelProvider === "claude"
                ? "bg-accent text-accent-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            Claude
          </button>
          <button
            type="button"
            onClick={() => setModelProvider("gemini")}
            className={[
              "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
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
            id="url-input"
            type="url"
            placeholder="yourwebsite.com"
            value={input}
            onChange={handleInputChange}
            className="h-12 ps-12 rounded-lg sm:rounded-r-none text-base font-sans"
            aria-invalid={!!error}
          />
        </div>
        <Button
          type="submit"
          size="lg"
          className="h-12 min-h-12 rounded-lg sm:rounded-l-none px-8 bg-accent text-accent-foreground hover:bg-accent/90 font-medium"
        >
          Redesign My Site
        </Button>
      </div>
      {error && <p className="text-sm text-destructive mt-2">{error}</p>}
    </form>
  );
}
