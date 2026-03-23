// web/src/components/progress/success-celebration.tsx
"use client";

import { useEffect, useState } from "react";

interface SuccessCelebrationProps {
  domain: string;
}

// Generate confetti particles with random trajectories
const PARTICLE_COUNT = 24;
const COLORS = [
  "oklch(0.72 0.12 75)",   // accent
  "oklch(0.65 0.15 45)",   // warm orange
  "oklch(0.70 0.14 140)",  // green
  "oklch(0.60 0.18 280)",  // purple
  "oklch(0.75 0.10 60)",   // gold
];

function generateParticles() {
  return Array.from({ length: PARTICLE_COUNT }, (_, i) => {
    const angle = (i / PARTICLE_COUNT) * 360 + Math.random() * 30;
    const distance = 80 + Math.random() * 120;
    const rad = (angle * Math.PI) / 180;
    return {
      id: i,
      x: Math.cos(rad) * distance,
      y: Math.sin(rad) * distance - 40, // bias upward
      color: COLORS[i % COLORS.length],
      size: 4 + Math.random() * 6,
      delay: Math.random() * 0.15,
      duration: 0.8 + Math.random() * 0.4,
    };
  });
}

export function SuccessCelebration({ domain }: SuccessCelebrationProps) {
  const [particles] = useState(generateParticles);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Trigger animation on next frame for CSS transition
    requestAnimationFrame(() => setVisible(true));
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-background">
      <div className="relative flex flex-col items-center">
        {/* Confetti particles */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none" aria-hidden="true">
          {particles.map((p) => (
            <span
              key={p.id}
              className="absolute rounded-full"
              style={{
                width: p.size,
                height: p.size,
                backgroundColor: p.color,
                ["--confetti-x" as string]: `${p.x}px`,
                ["--confetti-y" as string]: `${p.y}px`,
                animation: visible
                  ? `confetti-burst ${p.duration}s ${p.delay}s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards`
                  : "none",
              }}
            />
          ))}
        </div>

        {/* Celebration text */}
        <div
          className="flex flex-col items-center gap-4 z-10"
          style={{
            animation: visible
              ? "celebration-scale-in 0.6s 0.1s cubic-bezier(0.34, 1.56, 0.64, 1) forwards"
              : "none",
            opacity: 0,
          }}
        >
          <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-accent"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2.5}
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          </div>
          <h2 className="font-heading text-[clamp(1.5rem,4vw,2.5rem)] leading-[1.1] text-foreground text-center">
            Your redesign is ready!
          </h2>
          <p className="text-base text-muted-foreground text-center">
            Redirecting to your new <span className="text-accent font-medium">{domain}</span>...
          </p>
        </div>
      </div>
    </div>
  );
}
