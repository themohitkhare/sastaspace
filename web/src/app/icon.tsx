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
          background: "linear-gradient(135deg, #7c3aed 0%, #4f46e5 50%, #3730a3 100%)",
          borderRadius: "6px",
        }}
      >
        <svg
          width="22"
          height="22"
          viewBox="0 0 100 100"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Bold filled S — two offset semicircles forming a geometric S shape */}
          <path
            d="M68 28C68 14 56 6 44 6C32 6 22 14 22 26C22 38 32 42 44 46C56 50 68 54 68 66C68 78 56 86 44 86C32 86 22 78 22 64"
            stroke="rgba(255,255,255,0.95)"
            strokeWidth="16"
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
