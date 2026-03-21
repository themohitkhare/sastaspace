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
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #111111 0%, #1a1a1a 50%, #111111 100%)",
          fontFamily: "Inter, sans-serif",
          position: "relative",
        }}
      >
        {/* Subtle grid pattern overlay */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: "flex",
            opacity: 0.03,
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        />

        {/* Left side: Logo mark */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginRight: "60px",
          }}
        >
          <svg
            width="180"
            height="180"
            viewBox="0 0 100 100"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M70 25C70 25 65 10 50 10C35 10 25 22 25 32C25 52 70 42 70 62C70 75 58 90 43 90C28 90 22 75 22 75"
              stroke="#6366f1"
              strokeWidth="9"
              strokeLinecap="round"
              fill="none"
            />
            <circle cx="70" cy="25" r="5" fill="#e0e0e0" />
          </svg>
        </div>

        {/* Right side: Text */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-start",
          }}
        >
          <div
            style={{
              fontSize: "64px",
              fontWeight: 700,
              color: "#fafafa",
              letterSpacing: "-2px",
              lineHeight: 1.1,
            }}
          >
            SastaSpace
          </div>
          <div
            style={{
              fontSize: "24px",
              color: "#888888",
              marginTop: "12px",
              maxWidth: "420px",
              lineHeight: 1.4,
            }}
          >
            See your website redesigned by AI in 60 seconds
          </div>
          {/* Blue accent line */}
          <div
            style={{
              width: "60px",
              height: "3px",
              background: "#6366f1",
              marginTop: "24px",
              borderRadius: "2px",
            }}
          />
        </div>

        {/* Bottom-right subtle branding */}
        <div
          style={{
            position: "absolute",
            bottom: "24px",
            right: "32px",
            fontSize: "14px",
            color: "#555555",
            display: "flex",
          }}
        >
          sastaspace.com
        </div>
      </div>
    ),
    {
      ...size,
    }
  );
}
