import { AppShell } from "@/components/layout/app-shell";
import { ContactForm } from "@/components/contact-form";

export const metadata = {
  title: "Contact — SastaSpace",
};

export default function ContactPage() {
  return (
    <AppShell projectName="SastaSpace">
      <section className="mx-auto max-w-2xl px-4 py-16">
        <h1 className="text-3xl font-semibold tracking-tight">Get in touch</h1>
        <p className="mt-2 text-muted-foreground">
          Drop a note and it lands in our inbox. We read everything.
        </p>
        <div className="mt-8">
          <ContactForm source="landing" />
        </div>
      </section>
    </AppShell>
  );
}
