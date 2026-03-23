"use client";

import { useState } from "react";
import { Twitter, Linkedin, Link2, Check } from "lucide-react";

interface ShareButtonsProps {
  url: string;
  domain: string;
}

export function ShareButtons({ url, domain }: ShareButtonsProps) {
  const [copied, setCopied] = useState(false);

  const shareText = encodeURIComponent(`Check out my AI-redesigned website! ${url}`);
  const shareUrl = encodeURIComponent(url);

  const twitterHref = `https://twitter.com/intent/tweet?text=${shareText}`;
  const linkedinHref = `https://www.linkedin.com/sharing/share-offsite/?url=${shareUrl}`;

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available — silent fail
    }
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground mr-1">Share:</span>
      <a
        href={twitterHref}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center justify-center w-9 h-9 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors"
        aria-label={`Share ${domain} redesign on Twitter`}
      >
        <Twitter className="w-4 h-4" />
      </a>
      <a
        href={linkedinHref}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center justify-center w-9 h-9 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors"
        aria-label={`Share ${domain} redesign on LinkedIn`}
      >
        <Linkedin className="w-4 h-4" />
      </a>
      <button
        type="button"
        onClick={handleCopy}
        className="inline-flex items-center justify-center w-9 h-9 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors"
        aria-label="Copy link to clipboard"
      >
        {copied ? (
          <Check className="w-4 h-4 text-green-500" />
        ) : (
          <Link2 className="w-4 h-4" />
        )}
      </button>
      {copied && (
        <span className="text-xs text-green-500 font-medium animate-in fade-in duration-200">
          Copied!
        </span>
      )}
    </div>
  );
}
