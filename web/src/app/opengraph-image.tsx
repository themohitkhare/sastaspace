import { ImageResponse } from "next/og";

export const alt = "SastaSpace - AI Website Redesigner";
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";

export default function OgImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#0a0a0a",
          fontFamily: "Inter, system-ui, sans-serif",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Radial gradient bloom — indigo center glow */}
        <div
          style={{
            position: "absolute",
            top: "-200px",
            left: "50%",
            width: "900px",
            height: "900px",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(99,102,241,0.15) 0%, rgba(99,102,241,0.04) 40%, transparent 70%)",
            transform: "translateX(-50%)",
            display: "flex",
          }}
        />

        {/* Grid pattern — visible but subtle */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: "flex",
            opacity: 0.06,
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.15) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.15) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />

        {/* Small S mark as supporting element */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "56px",
            height: "56px",
            background: "linear-gradient(135deg, #7c3aed 0%, #4f46e5 50%, #3730a3 100%)",
            borderRadius: "12px",
            marginBottom: "32px",
          }}
        >
          <svg
            width="32"
            height="32"
            viewBox="0 0 100 100"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M68 28C68 14 56 6 44 6C32 6 22 14 22 26C22 38 32 42 44 46C56 50 68 54 68 66C68 78 56 86 44 86C32 86 22 78 22 64"
              stroke="rgba(255,255,255,0.95)"
              strokeWidth="16"
              strokeLinecap="round"
              fill="none"
            />
          </svg>
        </div>

        {/* Main title — large, gradient-like appearance */}
        <div
          style={{
            fontSize: "88px",
            fontWeight: 800,
            color: "#fafafa",
            letterSpacing: "-4px",
            lineHeight: 1,
            display: "flex",
          }}
        >
          SastaSpace
        </div>

        {/* Tagline — larger, more readable */}
        <div
          style={{
            fontSize: "30px",
            fontWeight: 400,
            color: "#9ca3af",
            marginTop: "20px",
            letterSpacing: "-0.5px",
            display: "flex",
          }}
        >
          See your website redesigned by AI in 60 seconds
        </div>

        {/* Bottom gradient line — premium glint */}
        <div
          style={{
            position: "absolute",
            bottom: "0",
            left: "0",
            right: "0",
            height: "2px",
            background: "linear-gradient(90deg, transparent 0%, #6366f1 30%, #8b5cf6 50%, #6366f1 70%, transparent 100%)",
            display: "flex",
          }}
        />
      </div>
    ),
    {
      ...size,
    }
  );
}
