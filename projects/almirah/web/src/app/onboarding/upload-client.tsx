"use client";

import { useRef, useState, type ChangeEvent } from "react";
import Link from "next/link";
import { IconCamera, IconSparkle } from "@/components/almirah/icons";
import type { ImageTagResult } from "@/lib/almirah/litellm";

type FileResult =
  | { status: "queued"; name: string }
  | { status: "processing"; name: string }
  | { status: "done"; name: string; result: ImageTagResult }
  | { status: "error"; name: string; message: string };

export function UploadClient() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [results, setResults] = useState<FileResult[]>([]);
  const [busy, setBusy] = useState(false);

  async function handlePick(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (files.length === 0) return;

    setBusy(true);
    setResults(files.map((f) => ({ status: "queued", name: f.name })));

    // Process serially — the remote model is small and concurrent calls can
    // overwhelm it. We could batch later.
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setResults((prev) =>
        prev.map((r, idx) => (idx === i ? { status: "processing", name: file.name } : r)),
      );

      try {
        const fd = new FormData();
        fd.append("image", file);
        const res = await fetch("/api/tag-image", { method: "POST", body: fd });
        const json = await res.json();
        if (!res.ok) throw new Error(json?.error || `HTTP ${res.status}`);
        setResults((prev) =>
          prev.map((r, idx) =>
            idx === i ? { status: "done", name: file.name, result: json.result } : r,
          ),
        );
      } catch (err) {
        const message = err instanceof Error ? err.message : "failed";
        setResults((prev) =>
          prev.map((r, idx) =>
            idx === i ? { status: "error", name: file.name, message } : r,
          ),
        );
      }
    }

    setBusy(false);
    if (inputRef.current) inputRef.current.value = "";
  }

  const done = results.filter((r) => r.status === "done").length;
  const errored = results.filter((r) => r.status === "error").length;
  const itemsFound = results.reduce(
    (n, r) => (r.status === "done" ? n + r.result.items_visible.length : n),
    0,
  );

  return (
    <div style={{ marginTop: 22, display: "flex", flexDirection: "column", gap: 14 }}>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        onChange={handlePick}
        disabled={busy}
        style={{ display: "none" }}
        id="almirah-photo-picker"
      />
      <label htmlFor="almirah-photo-picker" className="btn btn--primary btn--block">
        <IconCamera size={18} />
        <span>{busy ? "tagging…" : "pick photos →"}</span>
      </label>
      <Link
        href="/"
        className="btn btn--ghost btn--block"
        style={{ color: "var(--brand-muted)" }}
      >
        skip — I&apos;ll add items one at a time
      </Link>

      {results.length > 0 && (
        <>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}>
            <div className="statbox">
              <span className="lbl">photos</span>
              <span className="val">{results.length}</span>
            </div>
            <div className="statbox statbox--sasta">
              <span className="lbl">items found</span>
              <span className="val">{itemsFound}</span>
            </div>
            <div className="statbox statbox--ghost">
              <span className="lbl">done</span>
              <span className="val">
                {done}
                {errored ? ` · ${errored} err` : ""}
              </span>
            </div>
          </div>

          <div className="eyebrow" style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <IconSparkle size={12} />
            <span>what gemma saw</span>
          </div>
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
            {results.map((r, i) => (
              <li
                key={i}
                className="card"
                style={{ padding: 12, fontSize: 13, lineHeight: 1.45 }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <strong
                    style={{
                      fontWeight: 500,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      minWidth: 0,
                    }}
                  >
                    {r.name}
                  </strong>
                  <span className="meta-mono">{r.status}</span>
                </div>
                {r.status === "done" && (
                  <>
                    <div className="meta-mono" style={{ marginTop: 4 }}>
                      {r.result.style_family} · {r.result.occasion_hint || "—"} · {r.result.people_count}{" "}
                      person
                    </div>
                    <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                      {r.result.items_visible.map((it, idx) => (
                        <span key={idx} className="tag">
                          {it.colour} {it.kind}
                          {it.fabric_hint ? ` · ${it.fabric_hint}` : ""}
                        </span>
                      ))}
                      {r.result.items_visible.length === 0 && (
                        <span className="meta-mono">no items identified</span>
                      )}
                    </div>
                  </>
                )}
                {r.status === "error" && (
                  <div style={{ color: "var(--brand-sasta-text)", fontSize: 12, marginTop: 4 }}>
                    {r.message}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
