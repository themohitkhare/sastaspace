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
