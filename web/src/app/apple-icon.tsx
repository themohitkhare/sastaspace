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
          background: "linear-gradient(135deg, #7c3aed 0%, #4f46e5 50%, #3730a3 100%)",
          borderRadius: "36px",
          position: "relative",
        }}
      >
        {/* Inner glow for material depth */}
        <div
          style={{
            position: "absolute",
            top: "1px",
            left: "1px",
            right: "1px",
            bottom: "1px",
            borderRadius: "35px",
            border: "1px solid rgba(255,255,255,0.12)",
            display: "flex",
          }}
        />
        <svg
          width="110"
          height="110"
          viewBox="0 0 100 100"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Bold filled S — geometric, balanced */}
          <path
            d="M68 28C68 14 56 6 44 6C32 6 22 14 22 26C22 38 32 42 44 46C56 50 68 54 68 66C68 78 56 86 44 86C32 86 22 78 22 64"
            stroke="rgba(255,255,255,0.95)"
            strokeWidth="14"
            strokeLinecap="round"
            fill="none"
          />
        </svg>
      </div>
    ),
    {
      ...size,
    }
  );
}
