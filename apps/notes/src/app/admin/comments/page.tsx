"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/TopBar";
import { Footer } from "@/components/Footer";
import {
  deleteComment,
  isOwnerSignedIn,
  setStatus,
  subscribeAdminComments,
  type AdminComment,
} from "@/lib/admin";
import { subscribe as subscribeAuth, type Session } from "@/lib/auth";
import landingStyles from "@/app/notes.module.css";
import styles from "./admin.module.css";

export default function AdminCommentsPage() {
  const [session, setSession] = useState<Session | null>(null);
  const [rows, setRows] = useState<readonly AdminComment[] | null>(null);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => subscribeAuth((s) => setSession(s)), []);

  useEffect(() => {
    if (!isOwnerSignedIn()) {
      // Don't subscribe; the gate UI handles the not-owner branch.
      // (Setting state directly here would trigger a cascading render
      // and tripped the React 19 set-state-in-effect lint.)
      return;
    }
    setConnectError(null);
    return subscribeAdminComments(
      (r) => {
        setRows(r);
        setConnectError(null);
      },
      (err) => setConnectError(err.message ?? "connection failed"),
    );
  }, [session?.email]);

  async function action(id: number | bigint, kind: "approve" | "flag" | "delete") {
    const key = String(id);
    setBusyId(key);
    try {
      if (kind === "delete") await deleteComment(id);
      else await setStatus(id, kind === "approve" ? "approved" : "flagged");
    } catch (err) {
      console.error("admin action failed", err);
      window.alert(err instanceof Error ? err.message : "action failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className={landingStyles.wrap}>
      <TopBar />
      <main className={styles.main}>
        <div className={styles.eyebrow}>admin · comments</div>
        <h1 className={styles.heading}>Comment queue.</h1>

        {!session ? (
          <div className={styles.gate}>
            <p>Sign in with the owner email to use the admin queue.</p>
          </div>
        ) : !isOwnerSignedIn() ? (
          <div className={styles.gate}>
            <p>
              You're signed in as <strong>{session.email}</strong>, but only the lab owner can
              moderate. The reducer will reject any action you try.
            </p>
          </div>
        ) : connectError ? (
          <div className={styles.gate} role="alert">
            <p>
              <strong>Connection failed.</strong> {connectError}
            </p>
            <p>
              Refresh the page to retry. If the problem persists, check that
              your STDB token is current and the spacetime endpoint is up.
            </p>
          </div>
        ) : rows === null ? (
          <p className={styles.placeholder}>connecting…</p>
        ) : rows.length === 0 ? (
          <div className={styles.empty}>
            <p>The queue is empty. Either nothing's been submitted, or everything's already approved.</p>
          </div>
        ) : (
          <ul className={styles.list}>
            {rows.map((c) => (
              <li key={String(c.id)} className={styles.row}>
                <div className={styles.meta}>
                  <span className={`${styles.badge} ${styles[`status_${c.status}`]}`}>
                    {c.status}
                  </span>
                  <span className={styles.author}>{c.authorName}</span>
                  <span className={styles.dot}>·</span>
                  <span className={styles.slug}>{c.postSlug}</span>
                  <span className={styles.dot}>·</span>
                  <span className={styles.time}>
                    {new Date(c.createdAt).toISOString().slice(0, 16).replace("T", " ")}
                  </span>
                </div>
                <p className={styles.body}>{c.body}</p>
                <div className={styles.actions}>
                  {c.status !== "approved" && (
                    <button
                      className={styles.btnApprove}
                      onClick={() => action(c.id, "approve")}
                      disabled={busyId === String(c.id)}
                    >
                      approve
                    </button>
                  )}
                  {c.status !== "flagged" && (
                    <button
                      className={styles.btnFlag}
                      onClick={() => action(c.id, "flag")}
                      disabled={busyId === String(c.id)}
                    >
                      flag
                    </button>
                  )}
                  <button
                    className={styles.btnDelete}
                    onClick={() => action(c.id, "delete")}
                    disabled={busyId === String(c.id)}
                  >
                    delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
      <Footer />
    </div>
  );
}
