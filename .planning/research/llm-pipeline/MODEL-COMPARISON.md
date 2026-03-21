# Model Comparison: Open-Source LLMs for SastaSpace Pipeline

**Hardware target:** AMD RX 7900 XTX, 24GB VRAM, ROCm 6.3, gfx1100 (RDNA3)
**Inference engine:** vLLM (OpenAI-compatible, already deployed)
**Researched:** 2026-03-22

---

## Quick Reference: Does It Fit in 24GB?

| Model | Params | Active Params | INT4 VRAM | Fits 24GB? |
|-------|--------|---------------|-----------|------------|
| Qwen2.5-Coder-32B-Instruct | 32.5B | 32.5B (dense) | ~18–20 GB | YES (confirmed community) |
| Mistral Small 3.1 24B | 24B | 24B (dense) | ~12–14 GB | YES (confirmed) |
| Gemma 3 27B | 27B | 27B (dense) | ~14 GB | YES (INT4 QAT only; FP8 blocked) |
| DeepSeek-Coder-V2-Lite | 16B | 2.4B (MoE) | ~17 GB (Q8) | YES (with quantization) |
| Llama 3.3 70B Instruct | 70B | 70B (dense) | ~35–40 GB | NO — exceeds by ~15GB |
| Qwen2.5-72B-Instruct | 72B | 72B (dense) | ~37 GB | NO — exceeds by ~13GB |
| Mixtral 8x22B | 176B | ~39B (MoE) | ~66 GB | NO — far exceeds |
| DeepSeek-V3 | 671B | 37B (MoE) | ~380 GB | ABSOLUTELY NOT |

**Ruling out immediately:** Llama 3.3 70B, Qwen2.5-72B, Mixtral 8x22B, DeepSeek-V3. All require multi-GPU or much larger VRAM.

---

## Detailed Model Profiles

### 1. Qwen2.5-Coder-32B-Instruct

**Verdict: PRIMARY RECOMMENDATION for HTML/code generation stages**

| Property | Value |
|----------|-------|
| Parameters | 32.5B |
| Context window | 128K (default config 32K; needs rope_scaling for full 128K) |
| License | Apache 2.0 |
| VRAM (BF16) | ~65 GB |
| VRAM (GPTQ-Int4) | ~18–20 GB — fits 24GB with headroom |
| VRAM (GPTQ-Int8) | ~33 GB — does NOT fit |
| vLLM support | YES — officially supported |
| ROCm/gfx1100 | YES — community confirmed; requires `VLLM_USE_TRITON_FLASH_ATTN=0` |
| Quantization (ROCm) | GPTQ Int4 via `--quantization gptq_marlin` (NOT gptq_gemm, which is buggy) |
| HumanEval | 92.7% — best among open-source at this size |
| MMLU | 75.1% |
| Code Aider benchmark | 73.7 (comparable to GPT-4o) |
| IFEval | Not reported for coder variant |
| Structured output | YES via vLLM xgrammar (JSON schema constraint) |
| HTML generation | STRONG — trained on 5.5T tokens including source code; 40+ languages |

**Known issues on gfx1100:**
- No Flash Attention → falls back to reference implementation (slower but functional)
- High TTFT (time-to-first-token) reported as ~1796ms due to SWA fallback
- Must set `VLLM_USE_TRITON_FLASH_ATTN=0` for Qwen2.5 on ROCm
- AWQ not recommended on ROCm — use GPTQ-Int4 instead

**Official quantized models available:**
- `Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4` (HuggingFace)
- `Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int8` (needs 2x GPU)

**Sources:** huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct, qwenlm.github.io/blog/qwen2.5-coder-family/, llm-tracker.info/_TOORG/vLLM-on-RDNA3

---

### 2. Mistral Small 3.1 24B (Instruct-2503)

**Verdict: STRONG ALTERNATIVE for JSON/reasoning stages**

| Property | Value |
|----------|-------|
| Parameters | 24B |
| Context window | 128K |
| License | Apache 2.0 |
| VRAM (BF16/FP16) | ~55 GB |
| VRAM (GPTQ-Int4 / Q4_K_L GGUF) | ~12–14 GB — fits 24GB with significant headroom |
| vLLM support | YES — with `--tokenizer_mode mistral --config_format mistral --load_format mistral` |
| ROCm/gfx1100 | LIKELY YES (GPTQ works on gfx1100) but no community confirmation found |
| HumanEval | 88.41% |
| MMLU | 80.62% |
| IFEval | Not reported |
| Structured output | EXCELLENT — dedicated `--tool-call-parser mistral` flag in vLLM; JSON schema via xgrammar |

**Advantages over Qwen2.5-Coder-32B for JSON stages:**
- 24B vs 32B: leaves more VRAM headroom for KV cache at long contexts
- Mistral's tool-calling format is battle-tested and explicitly supported in vLLM
- Higher MMLU (80.62 vs 75.1) → better general reasoning for analysis stages

**Risk:** No confirmed community report of this exact model on gfx1100 with vLLM. Must validate before committing.

**Sources:** huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503

---

### 3. Gemma 3 27B IT

**Verdict: CONDITIONAL — good instruction-following but ROCm constraints**

| Property | Value |
|----------|-------|
| Parameters | 27B |
| Context window | 128K (vLLM caps at 64K to prevent OOM) |
| License | Google Gemma Terms of Use (NOT Apache/OSI-approved) |
| VRAM (BF16) | ~54 GB |
| VRAM (INT4 QAT) | ~14 GB — fits 24GB well |
| vLLM support | YES |
| ROCm/gfx1100 | PARTIAL — FP8 blocked (requires MI300+); BF16 + INT4 QAT should work |
| Structured output | YES — documented strength in instruction-following and structured output |

**Critical ROCm issue:** The FP8-dynamic variant fails on gfx1100 with "torch._scaled_mm is only supported on CUDA >= 9.0 or ROCm MI300+". Must use BF16 (too large) or INT4 QAT. BF16 doesn't fit; INT4 QAT does but needs the QAT-specific checkpoint.

**License concern:** Google Gemma Terms of Use, not Apache 2.0. Commercial use is permitted but you're subject to Google's AUP, not a clean open-source license. For a commercial product, prefer Apache 2.0.

**Recommendation:** Skip in favor of Qwen2.5-Coder-32B unless you need multimodal. The license complexity and FP8 limitation make it less attractive than Qwen.

---

### 4. DeepSeek-Coder-V2-Lite 16B

**Verdict: EFFICIENT OPTION for fast/cheap JSON stages**

| Property | Value |
|----------|-------|
| Total parameters | 16B |
| Active parameters | 2.4B (MoE sparse) |
| Context window | 128K |
| License | DeepSeek License (non-commercial restrictions — see below) |
| VRAM (BF16) | ~40 GB |
| VRAM (Q8_0 GGUF) | ~17 GB — fits 24GB |
| VRAM (Q4_K_M GGUF) | ~12 GB — fits 24GB comfortably |
| vLLM support | YES (merged support) |
| ROCm/gfx1100 | LIKELY (MoE vLLM models generally work; no specific gfx1100 report) |
| HumanEval | 90.2% (full 236B version) — Lite (16B) scores lower |
| Structured output | YES via vLLM xgrammar |

**MoE advantage:** Only 2.4B params activated per token → much faster inference than a dense 16B model. At Q8 (~17GB), leaves 7GB headroom for KV cache.

**License risk:** DeepSeek models have their own license that restricts certain commercial uses. Verify current terms at github.com/deepseek-ai/DeepSeek-Coder-V2/blob/main/LICENSE before using in production.

**Recommendation:** Good for fast CrawlAnalyst and QualityReviewer stages where speed matters more than peak quality. Not for HTMLGenerator (need strongest model there).

---

### 5. Llama 3.3 70B Instruct

**Verdict: DOES NOT FIT — ruled out for single 24GB GPU**

| Property | Value |
|----------|-------|
| Parameters | 70B |
| Context window | 128K |
| License | Meta Llama 3.3 Community License (commercial permitted; attribution required) |
| VRAM (INT4 AWQ/GPTQ) | ~35–40 GB |
| Fits 24GB? | NO — ~15GB over limit even at INT4 |
| HumanEval | 88.4% |
| MMLU | 86.0% |
| IFEval | 92.1% — best instruction-following among these models |

**If you add a second 24GB GPU:** Two RX 7900 XTX cards (48GB total) can run Llama 3.3 70B INT4 with `--tensor-parallel-size 2`. This would be the best general-purpose option for all stages. MEDIUM confidence on this due to limited vLLM tensor-parallel ROCm testing.

---

### 6. Qwen2.5-72B-Instruct

**Verdict: DOES NOT FIT — ruled out for single 24GB GPU**

| Property | Value |
|----------|-------|
| Parameters | 72B |
| Context window | 128K |
| License | Apache 2.0 |
| VRAM (INT4 AWQ) | ~37 GB |
| Fits 24GB? | NO |
| MMLU | ~86% |
| Structured output | YES |

Identical ruling as Llama 3.3 70B: requires ~37GB at INT4, cannot fit single 24GB.

---

### 7. Mixtral 8x22B

**Verdict: RULED OUT — 66GB at INT4**

Active parameters ~39B (uses 2 of 8 experts per token), but total parameter weight is 176B. At INT4, the full weight matrix is still ~66GB. Not viable on any single consumer GPU.

---

### 8. DeepSeek-V3 (full)

**Verdict: RULED OUT — requires ~380GB at Q4**

671B total parameters with 37B active per token. Requires 8–16 A100/H100 GPUs. Completely infeasible for self-hosting on a single gaming GPU.

---

### 9. CodeLlama (any variant)

**Verdict: SUPERSEDED — do not use**

CodeLlama's best variant (70B) is superseded by Llama 3.3 70B's code performance, and its 34B and 13B variants are superseded by Qwen2.5-Coder-32B/14B. Context window is limited to 16K in most deployed variants despite 100K training support. HumanEval scores are consistently lower than Qwen2.5-Coder equivalents. No reason to choose CodeLlama over Qwen2.5-Coder in 2025.

---

## Benchmark Comparison Table (models that fit 24GB)

| Model | HumanEval | MMLU | IFEval | Context | INT4 VRAM | License |
|-------|-----------|------|--------|---------|-----------|---------|
| Qwen2.5-Coder-32B | **92.7%** | 75.1% | N/A | 128K | ~18–20 GB | Apache 2.0 |
| Mistral Small 3.1 24B | 88.41% | **80.62%** | N/A | 128K | ~12–14 GB | Apache 2.0 |
| Gemma 3 27B | ~80%* | ~79%* | N/A | 128K | ~14 GB | Google ToU |
| DS-Coder-V2-Lite 16B | ~80%* | ~72%* | N/A | 128K | ~12 GB | DeepSeek License |

*Estimated from full model performance and parameter scaling; LOW confidence.

---

## ROCm / gfx1100 Compatibility Matrix

| Feature | Status on gfx1100 | Notes |
|---------|-------------------|-------|
| vLLM basic inference | WORKS | Since vLLM PR #2768; no flash-attention |
| BF16/FP16 | WORKS | Standard dtype |
| GPTQ Int4 (marlin) | WORKS | Use `--quantization gptq_marlin` |
| GPTQ Int4 (gemm) | BUGGY | Avoid; use marlin instead |
| AWQ | WORKS (slow) | Falls back to Triton kernels |
| FP8 | BLOCKED | Requires MI300+ or NVIDIA Ada/Hopper |
| Flash Attention | NOT AVAILABLE | Fallback used; increases TTFT |
| xgrammar (structured output) | WORKS | Upstreamed in vLLM v0.14.0 |
| Tensor parallel | WORKS | Needed for 70B models with 2x GPUs |
| GGUF | WORKS | vLLM added GGUF support for ROCm |

---

## Sources

- [Qwen2.5-Coder-32B-Instruct HuggingFace](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct)
- [Qwen2.5-Coder Family Blog](https://qwenlm.github.io/blog/qwen2.5-coder-family/)
- [Llama 3.3 70B HuggingFace](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct)
- [Mistral Small 3.1 HuggingFace](https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503)
- [Llama 3.3 vs Qwen2.5-Coder-32B Benchmark Comparison](https://llm-stats.com/models/compare/llama-3.3-70b-instruct-vs-qwen-2.5-coder-32b-instruct)
- [vLLM on RDNA3 compatibility guide](https://llm-tracker.info/_TOORG/vLLM-on-RDNA3)
- [ROCm Becomes First-Class Platform in vLLM](https://rocm.blogs.amd.com/software-tools-optimization/vllm-omni/README.html)
- [Gemma 3 27B FP8 on ROCm thread](https://discuss.vllm.ai/t/trying-to-run-gemma-3-27b-it-fp8-dynamic-with-rocm/1179)
- [vLLM Structured Outputs docs](https://docs.vllm.ai/en/latest/features/structured_outputs/)
- [vLLM Structured Decoding intro](https://blog.vllm.ai/2025/01/14/struct-decode-intro.html)
- [Gemma 3 QAT for consumer GPUs](https://developers.googleblog.com/en/gemma-3-quantized-aware-trained-state-of-the-art-ai-to-consumer-gpus/)
- [DeepSeek-Coder-V2 GitHub](https://github.com/deepseek-ai/DeepSeek-Coder-V2)
