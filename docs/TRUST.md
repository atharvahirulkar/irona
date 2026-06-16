# Trust model for local personal RAG

When you run a **pre-trained** model locally, weights are frozen — but **behavior** is shaped by what you retrieve, what tools you enable, and what you log. Irona treats those as first-class engineering, not add-ons.

---

## Assets and sensitivity

| Asset | Sensitivity | Irona handling |
|-------|-------------|------------------|
| Allowlisted folders | High (personal/academic) | Config roots only; no traversal outside |
| Retrieved chunks | High (prompt injection risk) | Passed as context; strict mode can block answer |
| Calendar events | Medium | Opt-in tool + approval |
| Web search results | Untrusted external | Labeled in prompt; opt-in + approval |
| Audit log | High (paths, queries) | `~/.irona/audit.log`, not in git |

---

## Threats (practical, not academic)

### 1. Over-collection

**Risk:** Agent reads more than the user expects.  
**Control:** `allowed_paths`, `enabled_tools`, interactive `/approve`, `/notes off`.

### 2. Wrong-grounding / hallucination

**Risk:** Model answers without correct file; sounds confident.  
**Control:** Citations in prompt, `/strict on`, **retrieval eval** (`irona eval`).

### 3. Prompt injection via documents

**Risk:** Malicious text in a PDF: “Ignore instructions and …”  
**Control:** Treat all file text as untrusted input; prefer answers that cite paths; test with one poisoned file in a dev folder (manual test).

### 4. Web poison

**Risk:** Search snippet manipulates the model.  
**Control:** `web.search` off by default; results prefixed as untrusted in `tools.py`.

### 5. No accountability

**Risk:** Cannot answer “what did the agent read?”  
**Control:** `append_audit` on prompts, tool grants, tool results.

---

## Defaults (secure-by-default)

- Tools denied unless in `enabled_tools`  
- `search_notes` allowed only with configured paths  
- Web and calendar require explicit config + runtime approval (when `require_tool_approval: true`)  
- No autonomous file writes  

See also [SECURITY.md](../SECURITY.md) for the short policy summary.

---

## What eval adds to trust

Retrieval metrics do not replace security — they show **when grounding fails even before the LLM speaks**. That gap is rarely measured in hobby local-RAG repos.

Run `irona eval` after changing chunk size, index, or allowlist paths.
