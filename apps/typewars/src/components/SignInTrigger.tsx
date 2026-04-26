"use client";
import { useState } from "react";
import { useSpacetimeDB } from "spacetimedb/react";
import { SignInModal } from "@sastaspace/auth-ui";

export function SignInTrigger() {
  const { identity } = useSpacetimeDB();
  const [open, setOpen] = useState(false);
  // Identity hex without the 0x prefix (auth service strips it anyway).
  const prevIdentity = identity ? identity.toHexString() : undefined;

  return (
    <>
      <button className="link-btn" onClick={() => setOpen(true)}>sign in →</button>
      <SignInModal
        app="typewars"
        callback="https://typewars.sastaspace.com/auth/callback"
        prevIdentity={prevIdentity}
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
