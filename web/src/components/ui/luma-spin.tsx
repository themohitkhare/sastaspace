"use client";

export function LumaSpin() {
  return (
    <div className="relative w-[65px] aspect-square">
      <span
        className="absolute rounded-[50px]"
        style={{ animation: "luma-anim 2.5s infinite", boxShadow: "inset 0 0 0 3px currentColor" }}
      />
      <span
        className="absolute rounded-[50px]"
        style={{
          animation: "luma-anim 2.5s infinite -1.25s",
          boxShadow: "inset 0 0 0 3px currentColor",
        }}
      />
    </div>
  );
}
