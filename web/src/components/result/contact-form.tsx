"use client";

import { useReducer, useRef } from "react";
import { AnimatePresence, m } from "motion/react";
import { Loader2 } from "lucide-react";
import { Turnstile, type TurnstileInstance } from "@marsidev/react-turnstile";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

interface ContactFormProps {
  subdomain: string;
}

type FormStatus = "idle" | "submitting" | "success" | "error";

interface FormState {
  status: FormStatus;
  name: string;
  email: string;
  message: string;
  honeypot: string;
  errors: Record<string, string>;
  serverError: string | null;
  turnstileToken: string | null;
}

type FormAction =
  | { type: "SET_FIELD"; field: "name" | "email" | "message" | "honeypot"; value: string }
  | { type: "SET_ERRORS"; errors: Record<string, string> }
  | { type: "SUBMIT" }
  | { type: "SUCCESS" }
  | { type: "FAILURE"; error: string }
  | { type: "SET_TURNSTILE"; token: string | null };

const initialState: FormState = {
  status: "idle",
  name: "",
  email: "",
  message: "",
  honeypot: "",
  errors: {},
  serverError: null,
  turnstileToken: null,
};

function formReducer(state: FormState, action: FormAction): FormState {
  switch (action.type) {
    case "SET_FIELD": {
      const errors = { ...state.errors };
      delete errors[action.field];
      return { ...state, [action.field]: action.value, errors };
    }
    case "SET_ERRORS":
      return { ...state, errors: action.errors };
    case "SUBMIT":
      return { ...state, status: "submitting", serverError: null };
    case "SUCCESS":
      return { ...state, status: "success" };
    case "FAILURE":
      return { ...state, status: "error", serverError: action.error };
    case "SET_TURNSTILE":
      return { ...state, turnstileToken: action.token };
  }
}

export function ContactForm({ subdomain }: ContactFormProps) {
  const turnstileEnabled =
    process.env.NEXT_PUBLIC_ENABLE_TURNSTILE !== "false";
  const [state, dispatch] = useReducer(formReducer, initialState);
  const turnstileRef = useRef<TurnstileInstance>(null);

  function validate(): Record<string, string> {
    const newErrors: Record<string, string> = {};
    if (!state.name.trim()) newErrors.name = "Please enter your name";
    if (!state.email.trim() || !/.+@.+\..+/.test(state.email)) {
      newErrors.email = "Please enter a valid email address";
    }
    if (!state.message.trim()) newErrors.message = "Please enter a message";
    return newErrors;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      dispatch({ type: "SET_ERRORS", errors: validationErrors });
      return;
    }

    dispatch({ type: "SUBMIT" });

    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: state.name.trim(),
          email: state.email.trim(),
          message: state.message.trim(),
          website: state.honeypot,
          turnstileToken: state.turnstileToken,
          subdomain,
        }),
      });

      const data = await res.json();

      if (data.ok) {
        dispatch({ type: "SUCCESS" });
      } else {
        dispatch({ type: "FAILURE", error: data.error || "Something went wrong. Please try again." });
      }
    } catch {
      dispatch({ type: "FAILURE", error: "Something went wrong. Please try again." });
    } finally {
      turnstileRef.current?.reset();
    }
  }

  return (
    <div className="w-full flex flex-col items-center">
      <AnimatePresence mode="wait">
        {state.status !== "success" ? (
          <m.div
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
                  value={state.name}
                  onChange={(e) => dispatch({ type: "SET_FIELD", field: "name", value: e.target.value })}
                  disabled={state.status === "submitting"}
                />
                {state.errors.name && (
                  <p className="text-sm text-destructive mt-2">{state.errors.name}</p>
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
                  value={state.email}
                  onChange={(e) => dispatch({ type: "SET_FIELD", field: "email", value: e.target.value })}
                  disabled={state.status === "submitting"}
                />
                {state.errors.email && (
                  <p className="text-sm text-destructive mt-2">
                    {state.errors.email}
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
                  value={state.message}
                  onChange={(e) => dispatch({ type: "SET_FIELD", field: "message", value: e.target.value })}
                  disabled={state.status === "submitting"}
                  className="flex w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-base md:text-sm text-foreground placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 outline-none resize-none disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50"
                />
                {state.errors.message && (
                  <p className="text-sm text-destructive mt-2">
                    {state.errors.message}
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
                value={state.honeypot}
                onChange={(e) => dispatch({ type: "SET_FIELD", field: "honeypot", value: e.target.value })}
              />

              {/* Invisible Turnstile — per D-09, D-11; conditional per FLAG-01 */}
              {turnstileEnabled && (
                <Turnstile
                  ref={turnstileRef}
                  siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY!}
                  onSuccess={(token) => dispatch({ type: "SET_TURNSTILE", token })}
                  onExpire={() => {
                    dispatch({ type: "SET_TURNSTILE", token: null });
                    turnstileRef.current?.reset();
                  }}
                  options={{ size: "invisible" }}
                />
              )}

              {/* Server error display */}
              {state.serverError && (
                <p className="text-sm text-destructive mt-2">{state.serverError}</p>
              )}

              {/* Submit button — per D-05 */}
              <Button
                type="submit"
                className="w-full h-11 mt-6 bg-accent text-accent-foreground hover:bg-accent/90"
                disabled={state.status === "submitting"}
              >
                {state.status === "submitting" ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  "Send Message"
                )}
              </Button>
            </form>
          </m.div>
        ) : (
          <m.div
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
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}
