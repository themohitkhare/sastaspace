import { SignUpForm } from "@/components/auth/sign-up-form";

export const metadata = { title: "Create account — udaan" };

export default function SignUpPage() {
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Create your account</h1>
        <p className="text-sm text-muted-foreground">Sign up to access udaan.</p>
      </div>
      <SignUpForm />
    </div>
  );
}
