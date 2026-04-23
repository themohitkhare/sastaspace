import { Suspense } from "react";
import { SignInForm } from "@/components/auth/sign-in-form";

export const metadata = { title: "Sign in — __NAME__" };

export default function SignInPage() {
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-[32px] font-medium leading-[1.1] tracking-[-0.02em]">Sign in.</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Back into the lab.
        </p>
      </div>
      <Suspense fallback={null}>
        <SignInForm />
      </Suspense>
    </div>
  );
}
