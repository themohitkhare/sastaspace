import { AppShell } from "@/components/layout/app-shell";
import { ContactForm } from "@/components/contact-form";

export const metadata = {
  title: "Say hi — sastaspace",
  description: "Drop a note. I read everything.",
};

export default function ContactPage() {
  return (
    <AppShell>
      <section className="mx-auto max-w-2xl px-6 pb-24 pt-16 sm:px-8 sm:pt-20">
        <div className="font-mono text-xs tracking-[0.08em] text-[var(--brand-sasta)]">
          ~/mohit · contact
        </div>
        <h1 className="mt-5 text-[44px] leading-[1.05] tracking-[-0.02em] sm:text-[56px]">
          Say hi.
        </h1>
        <p className="mt-2 font-deva text-base text-muted-foreground sm:text-lg">
          नमस्ते कहो.
        </p>
        <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-foreground/85">
          Drop a note. It lands in my inbox. I read everything — ideas for the
          lab, feedback on a project, or just a hello are all welcome.
        </p>
        <div className="mt-10">
          <ContactForm source="landing" />
        </div>
      </section>
    </AppShell>
  );
}
