# Pitfalls: Self-Hosted LLM Pipeline on AMD RX 7900 XTX

**Domain:** vLLM + ROCm + RDNA3 + multi-stage LLM pipeline
**Researched:** 2026-03-22

---

## Critical Pitfalls

### Pitfall 1: Wrong Quantization Format for gfx1100

**What goes wrong:** Deploying GPTQ models with the default `--quantization gptq` flag instead of `--quantization gptq_marlin`. The `gptq_gemm` kernel is buggy on ROCm and produces incorrect outputs or crashes.

**Why it happens:** vLLM's default GPTQ kernel selection doesn't auto-select marlin on ROCm. Documentation for CUDA doesn't apply to ROCm.

**Consequences:** Silent numeric errors in model outputs (wrong JSON, garbled HTML) or silent generation quality degradation.

**Prevention:** Always explicitly set `--quantization gptq_marlin` when loading GPTQ-quantized models on ROCm.

**Detection:** Compare outputs between `gptq` and `gptq_marlin` with the same prompt and seed. If outputs differ, marlin is correct.

---

### Pitfall 2: FP8 Models Fail Silently or Crash on gfx1100

**What goes wrong:** Loading any `*-fp8-dynamic` or `*-FP8*` model variant on an RX 7900 XTX. The error is `torch._scaled_mm is only supported on CUDA devices with compute capability >= 9.0 or 8.9, or ROCm MI300+`.

**Why it happens:** FP8 matrix multiplication is a hardware feature not present on RDNA3. It exists only on NVIDIA Ada/Hopper (RTX 40 series, H100) and AMD Instinct MI300+.

**Consequences:** Model fails to load; you may spend hours debugging environment issues that are actually hardware limitations.

**Prevention:** Only use BF16, FP16, GPTQ-Int4, GPTQ-Int8, or GGUF variants. Never use FP8 models on gfx1100.

**Detection:** Check model card for "fp8" in filename before downloading. Reject before attempting to load.

---

### Pitfall 3: 70B Models Don't Fit — Not Even at INT4

**What goes wrong:** Assuming INT4 quantization means a 70B model fits in 24GB. The math: 70B × 0.5 bytes = 35GB at INT4. Plus KV cache, CUDA graphs, and framework overhead, you need 40–45GB minimum.

**Why it happens:** Marketing often says "runs on consumer GPU" without specifying that means TWO 24GB GPUs.

**Consequences:** OOM crash during model load, or successful load but OOM during first inference with any reasonable context.

**Prevention:** Use the formula: `INT4 VRAM (GB) ≈ params_billions × 0.55`. For 70B: 70 × 0.55 = 38.5GB. Hard no for 24GB.

**Detection:** Check before downloading (saves hours). For 32B: 32 × 0.55 = 17.6GB → fits. For 24B: 24 × 0.55 = 13.2GB → fits with room.

---

### Pitfall 4: KV Cache Blows Up VRAM During Long Outputs

**What goes wrong:** Model weights load fine at 18–20GB, but inference OOMs when generating 15,000 tokens of HTML.

**Why it happens:** KV cache grows linearly with sequence length (input + output). At 32K total context, Qwen2.5-32B's KV cache adds ~4–6GB. At 64K context, it doubles.

**Consequences:** Inference crashes mid-generation, producing incomplete/corrupt HTML. The worst failure mode for the HTMLGenerator stage.

**Prevention:**
1. Set `--max-model-len 24576` (or lower) in vLLM to cap total sequence length
2. Set `--gpu-memory-utilization 0.90` to leave headroom
3. Monitor `rocm-smi` during test runs and observe actual peak VRAM

**Detection warning signs:** Generation starts fine but crashes at high token counts. VRAM usage grows during generation and approaches GPU limit.

---

### Pitfall 5: AWQ Is Slower Than Expected on ROCm

**What goes wrong:** Using AWQ-quantized models expecting performance parity with CUDA AWQ, then observing 2–3x slower token generation.

**Why it happens:** CUDA-native AWQ kernels are not available on ROCm. vLLM falls back to Triton implementations, which are significantly slower.

**Consequences:** Acceptable for occasional use but not for production pipeline with SLA requirements.

**Prevention:** Prefer GPTQ-Int4 (marlin) over AWQ for ROCm deployments. GPTQ marlin has proper ROCm kernel support.

---

### Pitfall 6: Flash Attention Fallback Causes High TTFT

**What goes wrong:** Time-to-first-token (TTFT) for Qwen2.5-Coder-32B on gfx1100 is ~1796ms, ~3–5x higher than on NVIDIA GPUs.

**Why it happens:** gfx1100 doesn't support Flash Attention. vLLM falls back to a reference O(n²) attention implementation, which is slower especially at long prompt lengths.

**Consequences:** For the SastaSpace use case (one pipeline run per user request, not high-concurrency serving), this is acceptable. For interactive use, it's sluggish.

**Prevention:** Accept this limitation. It's intrinsic to the hardware. Mitigations:
- Keep prompt lengths as short as possible (pre-process HTML before sending)
- Use `VLLM_USE_TRITON_FLASH_ATTN=0` to prevent any Triton flash attention attempt that may fail
- Consider prefill chunking (`--enable-chunked-prefill`) to reduce memory spikes

---

## Moderate Pitfalls

### Pitfall 7: Qwen2.5 Sliding Window Attention Warning on ROCm

**What goes wrong:** vLLM emits warnings or errors related to Sliding Window Attention (SWA) for Qwen2.5 models on ROCm. May cause inference to fall back to slower paths.

**Prevention:** Set `VLLM_USE_TRITON_FLASH_ATTN=0` before starting the vLLM server when using any Qwen2.5 family model on ROCm.

---

### Pitfall 8: xgrammar JSON Schema Timeout with Very Large Schemas

**What goes wrong:** The ComponentSelector stage sends a 2500-item component catalog as a JSON schema constraint. xgrammar may timeout or slow significantly when compiling a grammar from a very large schema.

**Why it happens:** xgrammar compiles the JSON schema into a grammar automaton at request time. Very large schemas (many properties, deep nesting) increase compilation time.

**Prevention:**
1. Don't use the full 2500-item catalog as a JSON schema. Instead, pre-filter to top-N candidates (e.g., top 50) based on keyword matching before sending to the model.
2. Or: use the model to output a list of component IDs (small schema), then do the lookup in Python.
3. xgrammar caches compiled grammars — reuse the same schema object across requests.

---

### Pitfall 9: Mistral Small 3.1 Requires Special vLLM Flags

**What goes wrong:** Loading `mistralai/Mistral-Small-3.1-24B-Instruct-2503` with standard vLLM flags causes tokenizer errors or broken tool calls.

**Prevention:** Always use the three-flag combination:
```
--tokenizer_mode mistral --config_format mistral --load_format mistral
```
And for tool calling: `--tool-call-parser mistral --enable-auto-tool-choice`.

---

### Pitfall 10: DeepSeek License for Commercial Use

**What goes wrong:** Using DeepSeek-Coder-V2-Lite in a commercial product (SastaSpace is a lead-gen tool) without reviewing their license.

**Prevention:** Read the DeepSeek license at github.com/deepseek-ai/DeepSeek-Coder-V2/blob/main/LICENSE before deploying. If restrictions apply, use Qwen2.5-Coder (Apache 2.0) instead. This is the primary reason DeepSeek is a secondary recommendation.

---

## Minor Pitfalls

### Pitfall 11: Model Download Size

Qwen2.5-Coder-32B-Instruct-GPTQ-Int4 is ~20GB on disk. Mistral Small 3.1 24B is ~13GB at Q4. Plan storage accordingly — if downloading to the k8s node, ensure the PVC has 50GB+ free.

### Pitfall 12: Cold Start Time

vLLM takes 40–90 seconds to load a 32B GPTQ model including kernel compilation. For a pipeline that runs infrequently, this is fine. For production latency requirements, keep the model loaded between requests (vLLM serves until explicitly stopped).

### Pitfall 13: ROCm Version Sensitivity

vLLM ROCm builds target specific ROCm versions. vLLM v0.14.0 requires ROCm 7.0 (per vLLM docs). Your current ROCm 6.3 may require using an older vLLM release or building from source. Verify the vLLM Docker image tag matches your ROCm version.

---

## Phase-Specific Warnings

| Stage | Likely Pitfall | Mitigation |
|-------|---------------|------------|
| CrawlAnalyst (JSON) | xgrammar schema errors | Use Pydantic schema → `.model_json_schema()` to generate valid JSON Schema |
| ComponentSelector | Large schema timeout | Pre-filter catalog to top-50 candidates before model call |
| HTMLGenerator | KV cache OOM at 20K tokens | Set `--max-model-len 24576`; monitor VRAM peak |
| HTMLNormalizer | Redundant large-output stage | Consider replacing with deterministic nh3 + BeautifulSoup cleanup |
| All stages | Slow TTFT | Expected on gfx1100; design UX with SSE streaming to hide latency |

---

## Sources

- [vLLM on RDNA3 compatibility notes](https://llm-tracker.info/_TOORG/vLLM-on-RDNA3)
- [Gemma 3 FP8 on ROCm failure](https://discuss.vllm.ai/t/trying-to-run-gemma-3-27b-it-fp8-dynamic-with-rocm/1179)
- [ROCm GPTQ quantization support](https://github.com/ModelCloud/GPTQModel)
- [vLLM xgrammar on ROCm](https://rocm.blogs.amd.com/software-tools-optimization/vllm-omni/README.html)
- [vLLM Structured Decoding intro](https://blog.vllm.ai/2025/01/14/struct-decode-intro.html)
- [Qwen2.5-Coder-32B GPTQ Int4 discussion](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4/discussions/1)
