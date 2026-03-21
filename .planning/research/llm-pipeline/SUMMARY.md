# Research Summary: Open-Source LLMs for SastaSpace AI Redesign Pipeline

**Domain:** Self-hosted LLM selection for multi-stage HTML generation pipeline
**Researched:** 2026-03-22
**Overall confidence:** MEDIUM — VRAM measurements are empirical from community, not always official. ROCm/gfx1100 specifics verified where possible.

---

## Executive Summary

The SastaSpace pipeline has 7 stages with distinct requirements. The core constraint is a single AMD RX 7900 XTX (24GB VRAM, gfx1100/RDNA3) with ROCm 6.3 and an existing vLLM deployment. This GPU architecture has specific limitations: no Flash Attention support, no FP8 (requires MI300+ or NVIDIA Ada/Hopper), no AWQ hardware kernels (falls back to Triton on ROCm). Supported quantization formats that work on gfx1100 are GPTQ (via marlin/bitblas kernels), BF16/FP16, and GGUF via vLLM's recently added GGUF support.

The key tension in model selection is: 70B models at INT4 still require ~35–40GB VRAM, making them impossible on a single 24GB GPU. 32B models at INT4 require ~18–20GB and fit comfortably. The strongest candidate for most pipeline stages — especially HTML generation — is **Qwen2.5-Coder-32B-Instruct-GPTQ-Int4**, which fits in 24GB VRAM, has verified ROCm/gfx1100 community usage, achieves HumanEval 92.7% (beating Llama 3.3 70B's 88.4%), and carries Apache 2.0 license.

For JSON-heavy stages (CrawlAnalyst, DesignStrategist, ComponentSelector, QualityReviewer), **Mistral Small 3.1 24B** is a compelling alternative at the same VRAM footprint — it has documented vLLM tool-calling/structured output integration with a dedicated `--tool-call-parser mistral` flag, Apache 2.0 license, and 128k context. However, it requires a ROCm-specific validation pass since community ROCm reports for gfx1100 are sparse.

A two-model deployment is the recommended architecture: one model optimized for code/HTML (Qwen2.5-Coder-32B), one for JSON/reasoning (Mistral Small 3.1 24B or Qwen2.5-32B-Instruct), loaded sequentially or concurrently if a second GPU is added.

---

## Key Findings

**Primary recommendation:** Qwen2.5-Coder-32B-Instruct GPTQ-Int4 — fits 24GB, GPTQ works on gfx1100 (via marlin kernels), HumanEval 92.7%, Apache 2.0, vLLM verified.

**Critical hardware constraint:** 70B models (Llama 3.3, Qwen2.5-72B) require 35–40GB VRAM even at INT4 — do NOT fit in 24GB. Must use 32B or smaller.

**ROCm quantization matrix:** FP8 does not work on gfx1100 (requires MI300+). AWQ falls back to Triton (functional but slower). GPTQ via marlin/bitblas works. BF16/FP16 works. GGUF via vLLM works.

**vLLM structured output on ROCm:** xgrammar backend was upstreamed in vLLM v0.14.0 with ROCm support. JSON schema–constrained generation (guided_json) works on AMD via xgrammar.

**DeepSeek-V3/Mixtral 8x22B are ruled out:** Both require multi-GPU setups far exceeding single 24GB (DeepSeek-V3 needs ~380GB Q4, Mixtral 8x22B needs ~66GB Q4).

---

## Implications for Roadmap

**Phase ordering for LLM integration:**

1. **Validate hardware** — Confirm Qwen2.5-Coder-32B-GPTQ-Int4 loads and runs on gfx1100 vLLM. Measure actual VRAM and tokens/sec.
2. **JSON stages first** — CrawlAnalyst and DesignStrategist with structured output / JSON schema constraints.
3. **Long-output stages last** — HTMLGenerator is the hardest stage (8k–20k token output). Validate output length limits.
4. **Quality gate** — QualityReviewer can use a smaller/faster model than the generator.

**Research flags:**
- HTMLGenerator at 20k tokens: needs empirical test; vLLM default max_new_tokens may need tuning.
- Qwen2.5-Coder-32B SWA issue on ROCm: set `VLLM_USE_TRITON_FLASH_ATTN=0`.
- GPTQ marlin kernel required: set `--quantization gptq_marlin` not `gptq` in vLLM.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| VRAM (32B models) | HIGH | 4-bit ~18–20GB confirmed by multiple community measurements |
| VRAM (70B models) | HIGH | INT4 ~35–40GB — does not fit 24GB, well-documented |
| ROCm/gfx1100 support | MEDIUM | Verified for vLLM + Qwen2.5 family; Mistral/Gemma3 less documented on consumer RDNA3 |
| Structured output / JSON | HIGH | vLLM xgrammar on ROCm confirmed in v0.14.0 changelog |
| Benchmark scores | HIGH | Official model cards and llm-stats.com verified |
| HTML generation quality | LOW | No HTML-specific benchmark exists; inferred from HumanEval + anecdotal community reports |
| Throughput (tok/s) | LOW | Limited 32B measurements on gfx1100; 7B Qwen = 270 tok/s gives directional guidance only |

---

## Gaps to Address

- No HTML-specific benchmark exists for any open-source model — quality must be validated empirically.
- Mistral Small 3.1 24B on gfx1100 with vLLM ROCm: no community confirmation found. Needs a test run.
- ComponentSelector stage requires JSON with 2500-item catalog lookup — test whether xgrammar handles schemas of this size without timeout.
- Long output (20k tokens) with GPTQ on vLLM: KV cache + model may exceed 24GB at long context. Needs measurement.
- Qwen2.5-Coder-32B sliding window attention warning on ROCm: set env var before deployment.
