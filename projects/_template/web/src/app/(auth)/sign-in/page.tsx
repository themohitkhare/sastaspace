import { Suspense } from "react";
import { SignInForm } from "@/components/auth/sign-in-form";

export const metadata = { title: "Sign in — __NAME__" };

export default function SignInPage() {
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
        <p className="text-sm text-muted-foreground">
          Sign in to continue to __NAME__.
        </p>
      </div>
      <Suspense fallback={null}>
        <SignInForm />
      </Suspense>
    </div>
  );
}
