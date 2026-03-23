"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Monitor, Tablet, Smartphone } from "lucide-react";

type DeviceMode = "desktop" | "tablet" | "mobile";

const DEVICE_CONFIG: Record<
  DeviceMode,
  { width: number; label: string; icon: typeof Monitor }
> = {
  desktop: { width: 1280, label: "Desktop", icon: Monitor },
  tablet: { width: 768, label: "Tablet", icon: Tablet },
  mobile: { width: 375, label: "Mobile", icon: Smartphone },
};

interface BeforeAfterSliderProps {
  originalUrl: string;
  redesignUrl: string;
}

export function BeforeAfterSlider({ originalUrl, redesignUrl }: BeforeAfterSliderProps) {
  const [splitPosition, setSplitPosition] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const [activeTab, setActiveTab] = useState<"before" | "after">("after");
  const [deviceMode, setDeviceMode] = useState<DeviceMode>("desktop");
  const [containerWidth, setContainerWidth] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const outerRef = useRef<HTMLDivElement>(null);

  // Measure the outer container width so we can compute the scale factor
  useEffect(() => {
    if (!outerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    observer.observe(outerRef.current);
    return () => observer.disconnect();
  }, []);

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

  const currentDevice = DEVICE_CONFIG[deviceMode];
  const isMobileFrame = deviceMode === "mobile";

  // For non-desktop modes, we render the iframe at the device's native width
  // then scale it down to fit the visible container. This forces the iframe
  // content to reflow at the correct viewport width.
  const deviceWidth = currentDevice.width;
  const isDesktop = deviceMode === "desktop";

  // Compute the max width the container should occupy (for tablet/mobile, cap it)
  const maxContainerPx = isDesktop ? containerWidth : Math.min(deviceWidth, containerWidth);
  // Scale factor: visible container width / iframe native width
  const scale = isDesktop ? 1 : containerWidth > 0 ? Math.min(1, maxContainerPx / deviceWidth) : 1;
  // The container's displayed height at this scale
  const iframeHeight = 800;
  const displayedHeight = iframeHeight * scale;

  return (
    <div className="w-full">
      {/* Device switcher — desktop only */}
      <div className="hidden md:flex flex-col items-center gap-2 mb-4">
        <div className="flex gap-1 p-1 rounded-lg bg-muted">
          {(Object.keys(DEVICE_CONFIG) as DeviceMode[]).map((mode) => {
            const { label, icon: Icon } = DEVICE_CONFIG[mode];
            const isActive = deviceMode === mode;
            return (
              <button
                key={mode}
                type="button"
                onClick={() => setDeviceMode(mode)}
                aria-label={`Preview as ${label}`}
                className={[
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  isActive
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                ].join(" ")}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden lg:inline">{label}</span>
              </button>
            );
          })}
        </div>
        {!isDesktop && (
          <p className="text-xs text-muted-foreground">
            Preview shows layout at {deviceWidth}px viewport width
          </p>
        )}
      </div>

      {/* Desktop: side-by-side slider */}
      <div ref={outerRef} className="hidden md:flex justify-center">
        <div
          ref={containerRef}
          className={[
            "relative select-none overflow-hidden transition-all duration-300",
            isMobileFrame
              ? "border-[12px] border-foreground/20 rounded-[2rem]"
              : "rounded-xl border border-border",
          ].join(" ")}
          style={{
            boxShadow: "var(--shadow-lg)",
            width: isDesktop ? "100%" : `${maxContainerPx}px`,
            height: isDesktop ? undefined : `${displayedHeight}px`,
            aspectRatio: isDesktop ? "16 / 9" : undefined,
          }}
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
              className="pointer-events-none border-0"
              title="Original website"
              style={{
                width: isDesktop ? "100%" : `${deviceWidth}px`,
                height: isDesktop ? "100%" : `${iframeHeight}px`,
                transform: isDesktop ? undefined : `scale(${scale})`,
                transformOrigin: "top left",
              }}
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
              className="pointer-events-none border-0"
              title="Redesigned website"
              style={{
                width: isDesktop ? "100%" : `${deviceWidth}px`,
                height: isDesktop ? "100%" : `${iframeHeight}px`,
                transform: isDesktop ? undefined : `scale(${scale})`,
                transformOrigin: "top left",
              }}
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
