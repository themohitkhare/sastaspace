"use client";

import { useState, useRef } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Loader2 } from "lucide-react";
import { Turnstile, type TurnstileInstance } from "@marsidev/react-turnstile";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

interface ContactFormProps {
  subdomain: string;
}

type FormStatus = "idle" | "submitting" | "success" | "error";

export function ContactForm({ subdomain }: ContactFormProps) {
  const turnstileEnabled =
    process.env.NEXT_PUBLIC_ENABLE_TURNSTILE !== "false";
  const [status, setStatus] = useState<FormStatus>("idle");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [honeypot, setHoneypot] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const turnstileRef = useRef<TurnstileInstance>(null);

  function validate(): Record<string, string> {
    const newErrors: Record<string, string> = {};
    if (!name.trim()) newErrors.name = "Please enter your name";
    if (!email.trim() || !/.+@.+\..+/.test(email)) {
      newErrors.email = "Please enter a valid email address";
    }
    if (!message.trim()) newErrors.message = "Please enter a message";
    return newErrors;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setStatus("submitting");
    setServerError(null);

    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          message: message.trim(),
          website: honeypot,
          turnstileToken,
          subdomain,
        }),
      });

      const data = await res.json();

      if (data.ok) {
        setStatus("success");
      } else {
        setServerError(data.error || "Something went wrong. Please try again.");
        setStatus("error");
      }
    } catch {
      setServerError("Something went wrong. Please try again.");
      setStatus("error");
    } finally {
      turnstileRef.current?.reset();
    }
  }

  return (
    <div className="w-full flex flex-col items-center">
      <AnimatePresence mode="wait">
        {status !== "success" ? (
          <motion.div
            key="form"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="w-full flex flex-col items-center"
          >
            <h2 className="font-heading text-[clamp(1.5rem,3vw,2rem)] text-foreground text-center mb-8">
              Like what you see? Let&apos;s build the real thing.
            </h2>
            <form onSubmit={handleSubmit} noValidate className="w-full max-w-xl space-y-4">
              <div>
                <Label htmlFor="contact-name" className="mb-2">
                  Name
                </Label>
                <Input
                  id="contact-name"
                  type="text"
                  placeholder="Your name"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    setErrors((prev) => {
                      const n = { ...prev };
                      delete n.name;
                      return n;
                    });
                  }}
                  disabled={status === "submitting"}
                />
                {errors.name && (
                  <p className="text-sm text-destructive mt-2">{errors.name}</p>
                )}
              </div>

              <div>
                <Label htmlFor="contact-email" className="mb-2">
                  Email
                </Label>
                <Input
                  id="contact-email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setErrors((prev) => {
                      const n = { ...prev };
                      delete n.email;
                      return n;
                    });
                  }}
                  disabled={status === "submitting"}
                />
                {errors.email && (
                  <p className="text-sm text-destructive mt-2">
                    {errors.email}
                  </p>
                )}
              </div>

              {/* Message field — native textarea styled to match Input */}
              <div>
                <Label htmlFor="contact-message" className="mb-2">
                  Message
                </Label>
                <textarea
                  id="contact-message"
                  rows={4}
                  placeholder="Tell me about your project..."
                  value={message}
                  onChange={(e) => {
                    setMessage(e.target.value);
                    setErrors((prev) => {
                      const n = { ...prev };
                      delete n.message;
                      return n;
                    });
                  }}
                  disabled={status === "submitting"}
                  className="flex w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-base md:text-sm text-foreground placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 outline-none resize-none disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50"
                />
                {errors.message && (
                  <p className="text-sm text-destructive mt-2">
                    {errors.message}
                  </p>
                )}
              </div>

              {/* Honeypot field — hidden, per D-10 */}
              <input
                type="text"
                name="website"
                tabIndex={-1}
                autoComplete="off"
                aria-hidden="true"
                className="absolute opacity-0 pointer-events-none h-0 w-0 overflow-hidden"
                value={honeypot}
                onChange={(e) => setHoneypot(e.target.value)}
              />

              {/* Invisible Turnstile — per D-09, D-11; conditional per FLAG-01 */}
              {turnstileEnabled && (
                <Turnstile
                  ref={turnstileRef}
                  siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY!}
                  onSuccess={setTurnstileToken}
                  onExpire={() => {
                    setTurnstileToken(null);
                    turnstileRef.current?.reset();
                  }}
                  options={{ size: "invisible" }}
                />
              )}

              {/* Server error display */}
              {serverError && (
                <p className="text-sm text-destructive mt-2">{serverError}</p>
              )}

              {/* Submit button — per D-05 */}
              <Button
                type="submit"
                className="w-full h-11 mt-6 bg-accent text-accent-foreground hover:bg-accent/90"
                disabled={status === "submitting"}
              >
                {status === "submitting" ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  "Send Message"
                )}
              </Button>
            </form>
          </motion.div>
        ) : (
          <motion.div
            key="thanks"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2 }}
            className="py-16 text-center"
          >
            <h2 className="font-heading text-2xl text-foreground">
              Thanks, I&apos;ll be in touch.
            </h2>
            <p className="text-base text-muted-foreground mt-2">
              I typically reply within 24 hours.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
