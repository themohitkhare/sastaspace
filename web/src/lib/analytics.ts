type EventName =
  | "redesign_started"
  | "redesign_progress"
  | "result_viewed"
  | "contact_form_submitted"
  | "contact_form_error"
  | "share_clicked"
  | "tier_selected";

export function trackEvent(event: EventName, data?: Record<string, unknown>) {
  // Non-blocking fire-and-forget
  try {
    const payload = { event, data, ts: Date.now(), url: window.location.pathname };
    // Send to backend analytics endpoint
    navigator.sendBeacon("/api/analytics", JSON.stringify(payload));
  } catch {
    // Silent fail — analytics should never break the app
  }
}
