// Mastra setup. Shared by Phase 1 W3 (deck-agent) and W4 (moderator-agent).
//
// Exports:
//  - `ollama`: an `ollama-ai-provider` instance pointing at env.OLLAMA_URL.
//    Use `ollama(modelId)` to get a LanguageModelV1 you can hand to a
//    Mastra `Agent`.
//  - `oneShotAgent({name, modelId, instructions})`: convenience factory for
//    a single-turn classifier-style Agent. Both detector + classifier in
//    moderator-agent use this shape; deck-agent can use it for short
//    one-shot prompts too. The shared `ollama` provider means HTTP keep-alive
//    + connection pooling are reused across agents.

import { Agent } from "@mastra/core/agent";
import { createOllama, type OllamaProvider } from "ollama-ai-provider";

import { env } from "./env.js";

// `ollama-ai-provider` expects the Ollama base URL with `/api` appended.
// `env.OLLAMA_URL` is the bare host (default http://127.0.0.1:11434), so
// strip a trailing slash and append `/api`.
export const ollama = createOllama({
  baseURL: `${env.OLLAMA_URL.replace(/\/$/, "")}/api`,
});

// Lazy variant for callers that want to defer provider construction past
// import time (e.g. deck-agent's start() flow). Returns the same singleton
// shape on each call so HTTP keep-alive is shared.
let _ollamaProvider: OllamaProvider | undefined;
export function ollamaProvider(): OllamaProvider {
  if (!_ollamaProvider) {
    _ollamaProvider = createOllama({
      baseURL: `${env.OLLAMA_URL.replace(/\/$/, "")}/api`,
    });
  }
  return _ollamaProvider;
}

// Kept for backwards-compat with anything still reading the old config map.
export const ollamaConfig = {
  baseURL: env.OLLAMA_URL,
  defaultModel: env.OLLAMA_MODEL,
};

export const localaiConfig = {
  baseURL: env.LOCALAI_URL,
};

export interface OneShotAgentOpts {
  name: string;
  modelId: string;
  instructions: string;
}

/** Spawns a single-turn Mastra Agent. The detector + classifier in
 *  moderator-agent.ts both call `.generate(...)` on the returned Agent
 *  with `temperature: 0` + `maxTokens: 5` to mimic the Python
 *  Agno+Ollama call shape.
 */
export function oneShotAgent(opts: OneShotAgentOpts): Agent {
  return new Agent({
    name: opts.name,
    instructions: opts.instructions,
    model: ollama(opts.modelId),
  });
}
