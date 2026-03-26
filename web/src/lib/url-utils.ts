export function validateUrl(input: string): {
  valid: boolean;
  url: string;
  error?: string;
} {
  const trimmed = input.trim();

  if (!trimmed) {
    return {
      valid: false,
      url: trimmed,
      error: "Please enter a valid website address",
    };
  }

  let urlString = trimmed;
  if (!/^https?:\/\//i.test(urlString)) {
    urlString = `https://${urlString}`;
  }

  try {
    const parsed = new URL(urlString);

    if (!parsed.hostname.includes(".")) {
      return {
        valid: false,
        url: trimmed,
        error: "Please enter a valid website address",
      };
    }

    return { valid: true, url: parsed.href };
  } catch {
    return {
      valid: false,
      url: trimmed,
      error: "Please enter a valid website address",
    };
  }
}

/**
 * Convert a SastaSpace subdomain slug back to a domain name.
 * Strips the version suffix (--2, --3, etc.) before converting.
 *
 * "ashwinkulkarni-com--2" → "ashwinkulkarni.com"
 * "mrbrownbakery-com"     → "mrbrownbakery.com"
 * "example-com--3"        → "example.com"
 */
export function subdomainToDomain(subdomain: string): string {
  const base = subdomain.replace(/--\d+$/, "");
  return base.replace(/-/g, ".");
}

export function extractDomain(url: string): string {
  try {
    let urlString = url.trim();
    if (!/^https?:\/\//i.test(urlString)) {
      urlString = `https://${urlString}`;
    }
    const parsed = new URL(urlString);
    return parsed.hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
