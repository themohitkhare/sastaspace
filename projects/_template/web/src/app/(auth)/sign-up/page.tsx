import { SignUpForm } from "@/components/auth/sign-up-form";

export const metadata = { title: "Create account — __NAME__" };

export default function SignUpPage() {
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Create your account</h1>
        <p className="text-sm text-muted-foreground">Sign up to access __NAME__.</p>
      </div>
      <SignUpForm />
    </div>
  );
}
