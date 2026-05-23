# The local pre-trained model gap

Most tutorials stop at: **pull a model → embed files → chat**. That teaches *how to call* an API, not *how to ship* a personal agent on real hardware with real data.

Cadbury exists to close gaps people skip when running **pre-trained models locally**:

---

## 1. Retrieval is unmeasured

Teams ship RAG and assume it works because answers *sound* right. On private PDFs, the failure mode is silent: wrong file ranked first, GPA buried in a 120-character snippet, syllabus chosen instead of a transcript.

**Cadbury response:** `cadbury eval` compares **keyword**, **semantic**, and **hybrid** retrieval on a gold question set you label. Speak with numbers: recall@1, recall@5, MRR — not vibes.

---

## 2. Permissions are an afterthought

Cloud products hide policy in terms of service. Local repos often give the model `os.walk("/")` energy with no audit trail.

**Cadbury response:** `allowed_paths`, `enabled_tools`, session `/approve`, and `~/.cadbury/audit.log`. The interesting engineering is **what the agent is allowed to do before inference**, not the model weights.

---

## 3. Edge constraints are ignored

A 7B model on 16 GB RAM is not a datacenter GPU. Cold-start embedding downloads, Ollama timeouts, and offline caches matter.

**Cadbury response:** Documented runbook (`cadbury doctor`), offline embedding load (`local_files_only`), and eval latency per retrieval mode — **systems thinking on a laptop**.

---

## 4. Grounding vs fluency

Small models fluently hallucinate when context is thin. Strict mode refuses to answer without retrieved context; citations force paths into the prompt.

**Cadbury response:** Separate **retrieval eval** (reproducible) from **generation eval** (optional, slower). Prove the pipeline finds the right file first; then study when the LLM still drifts.

---

## 5. Untrusted input from your own files

PDFs and web pages are prompt-injection surfaces. “Ignore previous instructions” in a syllabus is a security issue, not a parlor trick.

**Cadbury response:** Threat model in [TRUST.md](TRUST.md), web results labeled untrusted, strict mode for high-stakes answers.

---

## What this project is *not*

- Not a Siri competitor  
- Not fine-tuning a foundation model  
- Not “local ChatGPT with extra steps”  

## What it *is*

A **permissioned RAG agent lab** on macOS: inference (Ollama) + retrieval (measurable) + policy (auditable) + honest limits of 7B models.

That combination is what’s worth discussing in an MS Data Science interview — if you run the eval and can explain one row in the results table.
