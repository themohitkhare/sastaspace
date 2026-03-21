import { ImageResponse } from "next/og";

export const size = {
  width: 32,
  height: 32,
};
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#1a1a1a",
          borderRadius: "6px",
        }}
      >
        <svg
          width="22"
          height="22"
          viewBox="0 0 100 100"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Stylized S made from two arcs with blue accent */}
          <path
            d="M70 25C70 25 65 10 50 10C35 10 25 22 25 32C25 52 70 42 70 62C70 75 58 90 43 90C28 90 22 75 22 75"
            stroke="#6366f1"
            strokeWidth="12"
            strokeLinecap="round"
            fill="none"
          />
          {/* Subtle glow dot at top */}
          <circle cx="70" cy="25" r="4" fill="#e0e0e0" />
        </svg>
      </div>
    ),
    {
      ...size,
    }
  );
}
