"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { Globe } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { validateUrl, extractDomain } from "@/lib/url-utils";

interface UrlInputFormProps {
  onSubmit: (url: string) => void;
}

export function UrlInputForm({ onSubmit }: UrlInputFormProps) {
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [faviconUrl, setFaviconUrl] = useState<string | null>(null);
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

    onSubmit(result.url);
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="w-full max-w-xl">
      <div className="flex flex-col sm:flex-row gap-2 sm:gap-0 w-full">
        <div className="relative flex-1">
          <Label htmlFor="url-input" className="sr-only">
            Website URL
          </Label>
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground z-10">
            {faviconUrl ? (
              <img
                src={faviconUrl}
                alt=""
                className="w-5 h-5 rounded-sm"
                onError={() => setFaviconUrl(null)}
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
            className="h-12 ps-12 rounded-lg sm:rounded-r-none"
            aria-invalid={!!error}
          />
        </div>
        <Button
          type="submit"
          size="lg"
          className="h-11 min-h-11 rounded-lg sm:rounded-l-none px-6"
        >
          Redesign My Site
        </Button>
      </div>
      {error && <p className="text-sm text-destructive mt-2">{error}</p>}
    </form>
  );
}
