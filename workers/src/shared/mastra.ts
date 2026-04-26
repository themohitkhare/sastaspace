// Mastra setup. Phase 1 W3/W4 flesh this out once we know the exact
// provider package names the version we install settles on.

import { env } from "./env.js";

export const ollamaConfig = {
  baseURL: env.OLLAMA_URL,
  defaultModel: env.OLLAMA_MODEL,
};

export const localaiConfig = {
  baseURL: env.LOCALAI_URL,
};

// Mastra instance is created lazily by each agent that needs it, so agents
// that aren't enabled don't pay the import cost.
