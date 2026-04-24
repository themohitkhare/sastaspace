import Link from "next/link";
import { AppFrame } from "@/components/almirah/app-frame";
import { AppBar } from "@/components/almirah/app-bar";
import { IconClose } from "@/components/almirah/icons";
import { UploadClient } from "./upload-client";

export default function Onboarding() {
  return (
    <AppFrame>
      <AppBar
        terminal="step 1 of 1 — let's see what you've got"
        right={
          <Link href="/" className="iconbtn" aria-label="close">
            <IconClose />
          </Link>
        }
      />
      <div className="scroll scroll--pad">
        <h1 className="screen-title" style={{ marginTop: 8 }}>
          Dump your camera roll.
        </h1>
        <p className="screen-sub">
          Any photo with an item in it. We&apos;ll isolate every garment, dedupe the duplicates, and hang
          each one on its own rail. ~5 seconds per photo on-device — Gemma 4 running in our own cluster.
        </p>

        <div
          style={{
            marginTop: 22,
            padding: 14,
            border: "1px dashed var(--brand-dust-40)",
            borderRadius: 12,
          }}
        >
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            what the AI does
          </div>
          <ul style={{ margin: 0, padding: "0 0 0 16px", fontSize: 13, lineHeight: 1.7, color: "var(--brand-ink)" }}>
            <li>identifies every visible garment with Indian + western vocabulary</li>
            <li>extracts colour, fabric, silhouette, occasion hint</li>
            <li>dedupes across photos so one kurta = one rail entry</li>
            <li>nothing leaves our cluster — Gemma runs on the box at home</li>
          </ul>
        </div>

        <UploadClient />
      </div>
    </AppFrame>
  );
}
