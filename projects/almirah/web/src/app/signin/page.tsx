import { Suspense } from "react";
import { AppFrame } from "@/components/almirah/app-frame";
import { AppBar } from "@/components/almirah/app-bar";
import { BrandMark } from "@/components/almirah/brand-mark";
import { ItemSilhouette } from "@/components/almirah/item-shapes";
import { SignInForm } from "./signin-form";

export default function SignIn() {
  return (
    <AppFrame>
      <AppBar left={<span />} terminal="almirah.sastaspace.com —" />
      <div
        className="scroll scroll--pad"
        style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}
      >
        <div style={{ padding: "0 4px 40px" }}>
          <BrandMark size={44} />
          <h1
            className="screen-title"
            style={{ fontSize: 34, marginTop: 26, lineHeight: 1.1, letterSpacing: "-0.025em" }}
          >
            Your closet,
            <br />
            as a <span style={{ color: "var(--brand-sasta)" }}>rack.</span>
          </h1>
          <p className="screen-sub" style={{ fontSize: 15, marginTop: 14, lineHeight: 1.55 }}>
            Upload photos of what you own. We sort every kurta, saree, shirt, jutti into its own rail.
            Then the app dresses you — daily picks, occasion picks, missing pieces.
          </p>

          <div
            style={{
              marginTop: 30,
              padding: "10px 0 4px",
              borderTop: "1px solid var(--brand-dust-40)",
              borderBottom: "1px solid var(--brand-dust-40)",
              overflow: "hidden",
            }}
          >
            <div style={{ display: "flex", gap: 12, justifyContent: "space-between" }}>
              {(["kurta", "saree", "shirt", "jeans", "juttis"] as const).map((k, i) => (
                <div key={k} style={{ width: 48, color: "var(--brand-ink)", opacity: 0.75 - i * 0.08 }}>
                  <ItemSilhouette kind={k} size={48} />
                </div>
              ))}
            </div>
          </div>

          <Suspense>
            <SignInForm />
          </Suspense>

          <p
            style={{
              marginTop: 28,
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--brand-muted)",
              letterSpacing: "0.05em",
              lineHeight: 1.6,
            }}
          >
            one person · one closet · private by default
          </p>
        </div>
      </div>
    </AppFrame>
  );
}
