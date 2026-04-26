"use client";
import { useState } from "react";
import { useSpacetimeDB } from "spacetimedb/react";
import { SignInModal } from "@sastaspace/auth-ui";

// Phase 2 F2 flag. When "true", sign-in routes the magic-link callback to
// the new STDB-native /auth/verify page (which calls verify_token +
// claim_progress_self reducers directly). When unset/false, the legacy
// FastAPI /auth/callback#token=... fragment flow runs. Both paths coexist
// through Phase 3; flipped to true on prod after F1 lands.
const USE_STDB_AUTH = process.env.NEXT_PUBLIC_USE_STDB_AUTH === "true";

const TYPEWARS_ORIGIN =
  process.env.NEXT_PUBLIC_TYPEWARS_ORIGIN ?? "https://typewars.sastaspace.com";

export function SignInTrigger() {
  const { identity } = useSpacetimeDB();
  const [open, setOpen] = useState(false);
  // Identity hex without the 0x prefix (auth service strips it anyway, and the
  // STDB request_magic_link reducer accepts either shape).
  const prevIdentity = identity ? identity.toHexString() : undefined;
  const callback = USE_STDB_AUTH
    ? `${TYPEWARS_ORIGIN}/auth/verify`
    : `${TYPEWARS_ORIGIN}/auth/callback`;

  return (
    <>
      <button className="link-btn" onClick={() => setOpen(true)}>sign in →</button>
      <SignInModal
        app="typewars"
        callback={callback}
        prevIdentity={prevIdentity}
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
