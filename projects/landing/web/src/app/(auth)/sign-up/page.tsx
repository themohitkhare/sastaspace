import { SignUpForm } from "@/components/auth/sign-up-form";

export const metadata = { title: "Create account — sastaspace" };

export default function SignUpPage() {
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-[32px] font-medium leading-[1.1] tracking-[-0.02em]">Make an account.</h1>
        <p className="mt-2 text-sm text-muted-foreground">Needed for the admin-only corners of the lab.</p>
      </div>
      <SignUpForm />
    </div>
  );
}
