import { ImageResponse } from "next/og";

export const size = {
  width: 180,
  height: 180,
};
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%)",
          borderRadius: "36px",
        }}
      >
        <svg
          width="120"
          height="120"
          viewBox="0 0 100 100"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Stylized S lettermark */}
          <path
            d="M70 25C70 25 65 10 50 10C35 10 25 22 25 32C25 52 70 42 70 62C70 75 58 90 43 90C28 90 22 75 22 75"
            stroke="#6366f1"
            strokeWidth="10"
            strokeLinecap="round"
            fill="none"
          />
          {/* Accent dot */}
          <circle cx="70" cy="25" r="5" fill="#e0e0e0" />
        </svg>
      </div>
    ),
    {
      ...size,
    }
  );
}
