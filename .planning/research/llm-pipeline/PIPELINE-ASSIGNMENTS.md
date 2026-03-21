# Pipeline Stage → Model Assignments

**Hardware:** AMD RX 7900 XTX, 24GB VRAM, ROCm 6.3, vLLM
**Researched:** 2026-03-22

---

## Recommended Two-Model Architecture

Run two models sequentially from disk, or (if latency allows) keep one loaded persistently and hot-swap the other. The two-model split is:

- **Model A (Code/HTML):** `Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4` — ~18–20GB
- **Model B (JSON/Analysis):** `mistralai/Mistral-Small-3.1-24B-Instruct-2503` at Q4 — ~12–14GB

Running one at a time is fine for a pipeline with sequential stages. If you need concurrent execution, only Model B fits alongside a KV cache for Model A — budget carefully.

---

## Stage-by-Stage Assignments

### Stage 1: CrawlAnalyst
**Task:** Analyze crawled HTML/text → return structured JSON (SiteAnalysis)
**Output size:** Small (1–3KB JSON)
**Key requirement:** JSON schema compliance, general reasoning

**Recommended model:** Mistral Small 3.1 24B (Model B)
**Rationale:**
- Higher MMLU (80.62 vs 75.1) → better semantic understanding of site content
- Dedicated tool-call-parser in vLLM (`--tool-call-parser mistral`) = reliable JSON
- Small output → fast and doesn't need max context
- Apache 2.0, fits easily in 24GB

**vLLM config:**
```bash
vllm serve mistralai/Mistral-Small-3.1-24B-Instruct-2503 \
  --tokenizer_mode mistral \
  --config_format mistral \
  --load_format mistral \
  --tool-call-parser mistral \
  --enable-auto-tool-choice \
  --quantization gptq_marlin  # if using GPTQ variant
```

**Alternative:** Qwen2.5-Coder-32B-Instruct-GPTQ-Int4 if you only want one model loaded.

---

### Stage 2: DesignStrategist
**Task:** Produce design direction JSON (colors, fonts, layout style)
**Output size:** Small (1–2KB JSON)
**Key requirement:** JSON reliability, creative + analytical blend

**Recommended model:** Mistral Small 3.1 24B (Model B)
**Rationale:**
- Same as CrawlAnalyst — JSON reliability is the primary requirement
- Design decisions require cultural/stylistic knowledge → higher MMLU advantage applies
- Colors, fonts, layout are not code — reasoning > coding specialization

**Alternative:** Qwen2.5-Coder-32B works fine here too. Both produce reliable JSON via xgrammar.

---

### Stage 3: Copywriter
**Task:** Rewrite marketing copy
**Output size:** Medium (3–8KB text)
**Key requirement:** English quality, persuasive writing, brand voice

**Recommended model:** Mistral Small 3.1 24B (Model B)
**Rationale:**
- Copywriting is a language task, not a code task
- Mistral's higher MMLU suggests stronger language modeling
- No structured output required — just good prose
- Fastest option: small output, no JSON overhead

**Alternative:** Qwen2.5-32B-Instruct (the non-coder general variant) would be better still for pure text tasks, but adds a third model to manage. Mistral is an acceptable proxy.

---

### Stage 4: ComponentSelector
**Task:** Select UI components from a 2500-item JSON catalog
**Output size:** Medium JSON (list of component IDs + config)
**Key requirement:** JSON schema compliance with large input context (catalog), reasoning about design fit

**Recommended model:** Qwen2.5-Coder-32B-Instruct-GPTQ-Int4 (Model A)
**Rationale:**
- The 2500-item catalog is a large JSON input. Context window usage will be high (~20–40K tokens depending on catalog density)
- Qwen2.5-Coder handles structured data (JSON catalog) and selection tasks well — trained on code that includes JSON manipulation
- xgrammar constrained output enforces the selection schema

**Critical note:** The 2500-item catalog as input is the single biggest context risk in the pipeline. Test catalog tokenization before committing to this architecture. If catalog > 30K tokens, consider pre-filtering to top-N candidates before sending to the model.

**vLLM config:**
```bash
vllm serve Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4 \
  --quantization gptq_marlin \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.90 \
  -e VLLM_USE_TRITON_FLASH_ATTN=0 \
  -e PYTORCH_ROCM_ARCH=gfx1100
```

---

### Stage 5: HTMLGenerator
**Task:** Generate full HTML/CSS page (~100–200KB, 8k–20k tokens output)
**Output size:** LARGE (8,000–20,000 output tokens)
**Key requirement:** Long coherent output, valid HTML/CSS, code quality

**Recommended model:** Qwen2.5-Coder-32B-Instruct-GPTQ-Int4 (Model A)
**Rationale:**
- This is the hardest stage and the one where coding specialization matters most
- Qwen2.5-Coder 32B achieves HumanEval 92.7% vs Mistral's 88.4% — meaningful gap for HTML/CSS code quality
- Trained specifically on source code including HTML, CSS, JS — not just Python
- 128K context window supports large input (design spec + component list) + large output

**CRITICAL VRAM NOTE:** At GPTQ-Int4 (~18–20GB model weights), the KV cache for 20K output tokens at 32 layers, 64 heads, 128 head_dim in BF16 ≈ additional 4–6GB. Total may approach or exceed 24GB. Test with `--max-model-len 16384` first, then increase.

**Practical limits to validate:**
- Start with `--max-new-tokens 8192`
- Test with `--max-model-len 24576` (input + output budget)
- Monitor `nvidia-smi` / `rocm-smi` actual VRAM during generation

---

### Stage 6: QualityReviewer
**Task:** Score the output JSON (quality metrics, issues list)
**Output size:** Small JSON (scores + issues list)
**Key requirement:** Critical evaluation, JSON output, fast

**Recommended model:** Mistral Small 3.1 24B (Model B)
**Rationale:**
- Reviewing HTML for quality is an analytical task, not a generation task
- Fits easily, leaves headroom
- Fast (small output), which matters for latency

**Alternative:** For cheaper/faster option, DeepSeek-Coder-V2-Lite 16B (2.4B active params via MoE) runs at Q8 in ~17GB and would be very fast here. License risk applies.

---

### Stage 7: HTMLNormalizer
**Task:** Clean/fix the HTML (remove invalid tags, fix nesting, normalize whitespace)
**Output size:** Large (same size as HTMLGenerator output, ~8k–20k tokens)
**Key requirement:** HTML understanding, faithfulness to input (minimal change), code correctness

**Recommended model:** Qwen2.5-Coder-32B-Instruct-GPTQ-Int4 (Model A)
**Rationale:**
- Same model as HTMLGenerator — avoids a model swap
- Batch these two stages together: generate → normalize in the same vLLM session
- Qwen2.5-Coder's HTML understanding is the strongest among fitting models

**Alternative approach:** Instead of LLM normalization, use `nh3` (already in your stack) + an HTML parser (BeautifulSoup4, also already in stack) for deterministic normalization. Reserve the LLM for semantic fixes only. This reduces VRAM pressure and removes the second large-output stage.

---

## Single-Model Fallback

If managing two models is too complex, use only **Qwen2.5-Coder-32B-Instruct-GPTQ-Int4** for all 7 stages. You sacrifice ~5 MMLU points on language/reasoning stages but gain operational simplicity. The JSON output stages work fine via xgrammar regardless of model.

---

## Load Strategy Options

### Option A: Sequential Hot-Swap (recommended for low-traffic)
1. Load Model B (Mistral 24B) for stages 1–3
2. Unload, load Model A (Qwen 32B) for stages 4–5
3. Unload, reload Model B for stage 6
4. Keep Model A for stage 7 (or skip LLM normalization)

Total pipeline latency: 3 model loads + 7 inference passes. Each load is ~15–30 seconds.

### Option B: Single Model (Qwen2.5-Coder-32B only)
Load once, run all stages. Slight quality drop on language stages, much simpler ops.

### Option C: Two GPUs (if you add a second RX 7900 XTX)
48GB total VRAM enables Llama 3.3 70B INT4 (~35GB + KV cache). Run all stages with one stronger model. Also enables concurrent stage execution.

---

## vLLM Setup Commands (ROCm)

```bash
# Environment required for gfx1100
export PYTORCH_ROCM_ARCH="gfx1100"
export HSA_OVERRIDE_GFX_VERSION="11.0.0"
export VLLM_USE_TRITON_FLASH_ATTN=0  # Required for Qwen2.5 on ROCm

# Start Qwen2.5-Coder-32B GPTQ-Int4 (Model A)
docker run --device=/dev/kfd --device=/dev/dri \
  -e PYTORCH_ROCM_ARCH=gfx1100 \
  -e VLLM_USE_TRITON_FLASH_ATTN=0 \
  rocm/vllm:latest \
  vllm serve Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4 \
    --quantization gptq_marlin \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.90 \
    --port 8000

# Start Mistral Small 3.1 24B (Model B) - on different port
docker run --device=/dev/kfd --device=/dev/dri \
  rocm/vllm:latest \
  vllm serve mistralai/Mistral-Small-3.1-24B-Instruct-2503 \
    --tokenizer_mode mistral \
    --config_format mistral \
    --load_format mistral \
    --tool-call-parser mistral \
    --enable-auto-tool-choice \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.85 \
    --port 8001
```

---

## Structured Output Configuration (vLLM)

vLLM xgrammar backend handles JSON schema constraints. Use `response_format` in OpenAI-compatible requests:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")

response = client.chat.completions.create(
    model="Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4",
    messages=[{"role": "user", "content": prompt}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "SiteAnalysis",
            "schema": site_analysis_schema  # your Pydantic schema as dict
        }
    },
    max_tokens=2048,
)
```

This works on ROCm via xgrammar (confirmed in vLLM v0.14.0 ROCm changelog).

---

## Sources

- [vLLM Structured Outputs](https://docs.vllm.ai/en/latest/features/structured_outputs/)
- [vLLM ROCm v0.14.0 changelog](https://rocm.blogs.amd.com/software-tools-optimization/vllm-omni/README.html)
- [Qwen2.5 ROCm issues + workarounds](https://llm-tracker.info/_TOORG/vLLM-on-RDNA3)
- [Mistral vLLM serving guide](https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503)
- [Qwen2.5-Coder-32B-GPTQ-Int4](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-GPTQ-Int4)
