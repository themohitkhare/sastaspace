import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";

export const metadata = { title: "Reset password — __NAME__" };

export default function ForgotPasswordPage() {
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-[32px] font-medium leading-[1.1] tracking-[-0.02em]">Reset the password.</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Drop your email. Reset link arrives in your inbox.
        </p>
      </div>
      <ForgotPasswordForm />
    </div>
  );
}
