# Technology Stack: LLM Pipeline

**Project:** SastaSpace AI Redesign Pipeline
**Researched:** 2026-03-22

---

## Recommended Models

### Primary: HTML/Code Generation Stages

| Property | Value |
|----------|-------|
| Model | Qwen2.5-Coder-32B-Instruct-GPTQ-Int4 |
| Publisher | Alibaba (Qwen Team) |
| HuggingFace ID | `Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4` |
| License | Apache 2.0 |
| Context window | 128K (use 32K default; enable rope_scaling for longer) |
| VRAM (GPTQ-Int4) | ~18–20 GB on RX 7900 XTX |
| Benchmark | HumanEval 92.7%, MMLU 75.1%, Aider 73.7 |
| vLLM flag | `--quantization gptq_marlin` |
| Use for | ComponentSelector, HTMLGenerator, HTMLNormalizer |

**Why:** Best-in-class open-source coding model that fits 24GB. HumanEval 92.7% is the highest among sub-40B models. Code training corpus includes HTML, CSS, JS. Apache 2.0 — no commercial restrictions. gfx1100 community usage confirmed.

### Secondary: JSON/Analysis Stages

| Property | Value |
|----------|-------|
| Model | Mistral-Small-3.1-24B-Instruct-2503 |
| Publisher | Mistral AI |
| HuggingFace ID | `mistralai/Mistral-Small-3.1-24B-Instruct-2503` |
| License | Apache 2.0 |
| Context window | 128K |
| VRAM (GPTQ-Int4 / Q4 GGUF) | ~12–14 GB |
| Benchmark | HumanEval 88.41%, MMLU 80.62% |
| vLLM flags | `--tokenizer_mode mistral --config_format mistral --load_format mistral --tool-call-parser mistral` |
| Use for | CrawlAnalyst, DesignStrategist, Copywriter, QualityReviewer |

**Why:** Higher MMLU than Qwen2.5-Coder for general reasoning tasks. Dedicated vLLM tool-call-parser for reliable JSON. Smaller VRAM footprint leaves headroom for KV cache. Apache 2.0.

**Validation required:** No confirmed gfx1100 community report. Must run a test inference before committing.

---

## Inference Engine

| Technology | Version | Why |
|------------|---------|-----|
| vLLM | Latest stable (v0.14.0+) | Already deployed; OpenAI-compatible; xgrammar structured output on ROCm; GPTQ marlin support |
| ROCm Docker image | `rocm/vllm:latest` | Official pre-built image; as of Jan 2026, no source build needed |

**Alternative serving engine:** If vLLM proves unstable on gfx1100 for 32B models, fall back to `llama.cpp` with ROCm backend (Vulkan or HIP). llama.cpp + GGUF Q4_K_M has confirmed performance on RX 7900 XTX. Slower for batched requests but more stable.

---

## Quantization Strategy

| Stage | Model | Quantization | Disk Size | VRAM |
|-------|-------|-------------|-----------|------|
| JSON stages | Mistral Small 3.1 24B | Q4_K_L GGUF or GPTQ-Int4 | ~13 GB | ~12–14 GB |
| Code stages | Qwen2.5-Coder-32B | GPTQ-Int4 | ~20 GB | ~18–20 GB |

**Never use:** FP8 (requires MI300+), AWQ (slow Triton fallback on ROCm)

**GPTQ kernel to use:** `gptq_marlin` — NOT `gptq` or `gptq_gemm` (buggy on ROCm)

---

## Structured Output Backend

| Technology | Why |
|------------|-----|
| vLLM xgrammar | Upstreamed in v0.14.0 with ROCm support; low overhead; JSON schema → constrained decoding |

Usage in OpenAI-compatible client:
```python
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "SiteAnalysis",
        "schema": SiteAnalysis.model_json_schema()
    }
}
```

All Pydantic models in `sastaspace/` can generate JSON schemas via `.model_json_schema()`. This is the adapter between Python types and vLLM's constrained generation.

---

## Environment Variables (required for gfx1100)

```bash
PYTORCH_ROCM_ARCH=gfx1100
HSA_OVERRIDE_GFX_VERSION=11.0.0
VLLM_USE_TRITON_FLASH_ATTN=0   # Required for Qwen2.5 family
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| HTML generation | Qwen2.5-Coder-32B INT4 | Llama 3.3 70B INT4 | Doesn't fit 24GB (~38GB at INT4) |
| JSON analysis | Mistral Small 3.1 24B | Qwen2.5-Coder-32B | Qwen works but lower MMLU; both acceptable |
| Fast/cheap stages | Mistral Small 3.1 24B | DS-Coder-V2-Lite 16B | DeepSeek license risk; save for if Mistral fails |
| Quantization | GPTQ-Int4 (marlin) | AWQ | AWQ falls back to slow Triton on ROCm |
| Quantization | GPTQ-Int4 (marlin) | FP8 | FP8 blocked on gfx1100 |
| Inference engine | vLLM | llama.cpp | vLLM already deployed; GGUF is fallback only |
| All coding tasks | Qwen2.5-Coder-32B | CodeLlama 34B | CodeLlama superseded; lower benchmarks, older codebase |

---

## Future Upgrade Path

If the server gets a second RX 7900 XTX (48GB total):
- Use Llama 3.3 70B INT4 with `--tensor-parallel-size 2` for all stages
- Higher IFEval (92.1%) and MMLU (86.0%) improve JSON and reasoning stages
- Simplified ops: one model for everything

If the server gets an AMD Instinct MI300X (192GB):
- Use Qwen2.5-72B-Instruct in BF16 for all stages
- No quantization degradation
- FP8 becomes available

---

## Sources

- [Qwen2.5-Coder-32B-Instruct HuggingFace](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct)
- [Qwen2.5-Coder-32B-Instruct-GPTQ-Int4](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4)
- [Mistral Small 3.1 HuggingFace](https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503)
- [vLLM Quantization docs](https://docs.vllm.ai/en/latest/features/quantization/)
- [ROCm vLLM v0.14.0 blog](https://rocm.blogs.amd.com/software-tools-optimization/vllm-omni/README.html)
- [GPTQModel ROCm support](https://github.com/ModelCloud/GPTQModel)
