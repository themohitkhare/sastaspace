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
          background: "#1a1714",
          fontFamily: "Inter, system-ui, sans-serif",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Radial gradient bloom — warm amber glow */}
        <div
          style={{
            position: "absolute",
            top: "-200px",
            left: "50%",
            width: "900px",
            height: "900px",
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(200,153,58,0.12) 0%, rgba(200,153,58,0.03) 40%, transparent 70%)",
            transform: "translateX(-50%)",
            display: "flex",
          }}
        />

        {/* Grid pattern */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: "flex",
            opacity: 0.04,
            backgroundImage:
              "linear-gradient(rgba(200,153,58,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(200,153,58,0.3) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />

        {/* S mark */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "56px",
            height: "56px",
            background: "#1a1714",
            border: "2px solid rgba(200,153,58,0.3)",
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
              stroke="#c8993a"
              strokeWidth="16"
              strokeLinecap="round"
              fill="none"
            />
          </svg>
        </div>

        {/* Main title */}
        <div
          style={{
            fontSize: "88px",
            fontWeight: 800,
            color: "#f5f0e8",
            letterSpacing: "-4px",
            lineHeight: 1,
            display: "flex",
          }}
        >
          SastaSpace
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: "30px",
            fontWeight: 400,
            color: "#8a8070",
            marginTop: "20px",
            letterSpacing: "-0.5px",
            display: "flex",
          }}
        >
          See your website redesigned by AI in 60 seconds
        </div>

        {/* Bottom gradient line — warm amber glint */}
        <div
          style={{
            position: "absolute",
            bottom: "0",
            left: "0",
            right: "0",
            height: "2px",
            background:
              "linear-gradient(90deg, transparent 0%, #c8993a 30%, #dbb050 50%, #c8993a 70%, transparent 100%)",
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
