import { ImageResponse } from "next/og";
import type { NextRequest } from "next/server";
import { subdomainToDomain } from "@/lib/url-utils";

export const runtime = "edge";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const subdomain = searchParams.get("subdomain") ?? "your-site";
  const domain = subdomainToDomain(subdomain);

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
        {/* Radial gradient bloom */}
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
            width: "48px",
            height: "48px",
            background: "#1a1714",
            border: "2px solid rgba(200,153,58,0.3)",
            borderRadius: "10px",
            marginBottom: "24px",
          }}
        >
          <svg
            width="28"
            height="28"
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

        {/* Domain name — the hero text */}
        <div
          style={{
            fontSize: "72px",
            fontWeight: 800,
            color: "#f5f0e8",
            letterSpacing: "-3px",
            lineHeight: 1,
            display: "flex",
            textAlign: "center",
            maxWidth: "1000px",
          }}
        >
          {domain}
        </div>

        {/* AI-Redesigned tagline */}
        <div
          style={{
            fontSize: "32px",
            fontWeight: 500,
            color: "#c8993a",
            marginTop: "20px",
            letterSpacing: "-0.5px",
            display: "flex",
          }}
        >
          AI-Redesigned
        </div>

        {/* Branding */}
        <div
          style={{
            fontSize: "20px",
            fontWeight: 400,
            color: "#8a8070",
            marginTop: "12px",
            display: "flex",
          }}
        >
          by SastaSpace
        </div>

        {/* Bottom gradient line */}
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
      width: 1200,
      height: 630,
    }
  );
}
