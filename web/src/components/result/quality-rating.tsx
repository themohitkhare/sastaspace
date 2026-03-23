"use client";

import { useState, useEffect, useCallback } from "react";
import { Star } from "lucide-react";

interface QualityRatingProps {
  subdomain: string;
}

const STORAGE_KEY_PREFIX = "sastaspace-rating-";

export function QualityRating({ subdomain }: QualityRatingProps) {
  const [rating, setRating] = useState<number>(0);
  const [hoveredStar, setHoveredStar] = useState<number>(0);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(`${STORAGE_KEY_PREFIX}${subdomain}`);
    if (stored) {
      setRating(parseInt(stored, 10));
      setSubmitted(true);
    }
  }, [subdomain]);

  const submitRating = useCallback(
    async (value: number) => {
      setRating(value);
      setSubmitted(true);
      localStorage.setItem(`${STORAGE_KEY_PREFIX}${subdomain}`, String(value));

      try {
        await fetch("/api/rating", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ subdomain, rating: value }),
        });
      } catch {
        // Rating submission failure is non-blocking
      }
    },
    [subdomain]
  );

  return (
    <div className="flex flex-col items-center gap-3">
      <p className="text-sm text-muted-foreground">
        {submitted ? "Thanks for your feedback!" : "Rate this redesign"}
      </p>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => {
          const filled = submitted
            ? star <= rating
            : star <= (hoveredStar || rating);
          return (
            <button
              key={star}
              type="button"
              disabled={submitted}
              onClick={() => submitRating(star)}
              onMouseEnter={() => !submitted && setHoveredStar(star)}
              onMouseLeave={() => !submitted && setHoveredStar(0)}
              className="p-1 transition-transform hover:scale-110 disabled:cursor-default disabled:hover:scale-100"
              aria-label={`Rate ${star} star${star > 1 ? "s" : ""}`}
            >
              <Star
                className={`w-6 h-6 transition-colors ${
                  filled
                    ? "fill-accent text-accent"
                    : "fill-transparent text-muted-foreground/30"
                }`}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}
