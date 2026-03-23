"use client";

import { useState, useRef, useCallback, useEffect } from "react";

interface BeforeAfterSliderProps {
  originalUrl: string;
  redesignUrl: string;
}

export function BeforeAfterSlider({ originalUrl, redesignUrl }: BeforeAfterSliderProps) {
  const [splitPosition, setSplitPosition] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const [activeTab, setActiveTab] = useState<"before" | "after">("after");
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMove = useCallback(
    (clientX: number) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = clientX - rect.left;
      const percent = Math.max(0, Math.min(100, (x / rect.width) * 100));
      setSplitPosition(percent);
    },
    [],
  );

  const handleMouseDown = useCallback(() => {
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    function onMouseMove(e: MouseEvent) {
      e.preventDefault();
      handleMove(e.clientX);
    }

    function onMouseUp() {
      setIsDragging(false);
    }

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [isDragging, handleMove]);

  useEffect(() => {
    if (!isDragging) return;

    function onTouchMove(e: TouchEvent) {
      if (e.touches.length === 1) {
        handleMove(e.touches[0].clientX);
      }
    }

    function onTouchEnd() {
      setIsDragging(false);
    }

    window.addEventListener("touchmove", onTouchMove, { passive: true });
    window.addEventListener("touchend", onTouchEnd);
    return () => {
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onTouchEnd);
    };
  }, [isDragging, handleMove]);

  return (
    <div className="w-full">
      {/* Desktop: side-by-side slider */}
      <div className="hidden md:block">
        <div
          ref={containerRef}
          className="relative w-full aspect-[4/3] sm:aspect-video rounded-xl overflow-hidden border border-border select-none"
          style={{ boxShadow: "var(--shadow-lg)" }}
          onMouseDown={handleMouseDown}
          onTouchStart={(e) => {
            setIsDragging(true);
            if (e.touches.length === 1) {
              handleMove(e.touches[0].clientX);
            }
          }}
        >
          {/* Before (original) — full width, clipped from right */}
          <div
            className="absolute inset-0 z-10"
            style={{ clipPath: `inset(0 ${100 - splitPosition}% 0 0)` }}
          >
            <iframe
              src={originalUrl}
              sandbox="allow-scripts"
              className="w-full h-full pointer-events-none"
              title="Original website"
            />
            <div className="absolute top-4 left-4 bg-background/80 backdrop-blur-sm text-foreground text-xs font-medium px-3 py-1.5 rounded-full border border-border">
              Before
            </div>
          </div>

          {/* After (redesigned) — full width, visible on the right */}
          <div className="absolute inset-0">
            <iframe
              src={redesignUrl}
              sandbox="allow-scripts"
              className="w-full h-full pointer-events-none"
              title="Redesigned website"
            />
            <div className="absolute top-4 right-4 bg-accent/90 backdrop-blur-sm text-accent-foreground text-xs font-medium px-3 py-1.5 rounded-full">
              After
            </div>
          </div>

          {/* Divider line */}
          <div
            className="absolute top-0 bottom-0 z-20 w-0.5 bg-foreground/60"
            style={{ left: `${splitPosition}%` }}
          >
            {/* Drag handle */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-background border-2 border-foreground/60 flex items-center justify-center cursor-ew-resize shadow-lg">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-foreground/70">
                <path d="M5 3L2 8L5 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M11 3L14 8L11 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile: toggle tabs */}
      <div className="md:hidden">
        <div className="flex gap-1 p-1 rounded-lg bg-muted w-fit mx-auto mb-3">
          <button
            type="button"
            onClick={() => setActiveTab("before")}
            className={[
              "px-4 py-1.5 rounded-md text-sm font-medium transition-colors",
              activeTab === "before"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            Before
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("after")}
            className={[
              "px-4 py-1.5 rounded-md text-sm font-medium transition-colors",
              activeTab === "after"
                ? "bg-accent text-accent-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            After
          </button>
        </div>
        <div className="relative w-full aspect-[4/3] rounded-xl overflow-hidden border border-border" style={{ boxShadow: "var(--shadow-lg)" }}>
          <iframe
            src={activeTab === "before" ? originalUrl : redesignUrl}
            sandbox="allow-scripts"
            className="w-full h-full"
            title={activeTab === "before" ? "Original website" : "Redesigned website"}
          />
        </div>
      </div>
    </div>
  );
}
