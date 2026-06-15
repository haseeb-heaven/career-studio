# PDF Stack Rewrite — Design Spec
**Date:** 2026-06-15  
**Status:** Approved  
**Branch:** `refactor/pdf-stack`  
**Files changed:** `backend/parsers/pdf_parser.py`, `backend/exporters/pdf_exporter.py`, `backend/requirements.txt`

---

## Problem Statement

The current PDF stack has three independent failure classes:

1. **Parser extraction** — `pdfplumber.extract_text()` discards coordinate/font data, so section detection relies on ALL-CAPS keyword matching and name-is-first-line assumptions. Scanned PDFs silently produce empty profiles. Corrupt PDFs crash with unhandled 500s. Table-formatted skills are lost.

2. **Exporter style registry** — ReportLab's `ParagraphStyle` uses a process-global registry keyed by name. Repeated `export()` calls within the same process collide on style names; the current `cs-` prefix is a workaround, not a fix. There is also no proper Unicode support.

3. **Dependency bloat** — `pypdfium2` (15 MB native binary) is imported nowhere. `pdfminer.six` is explicitly pinned as a transitive dependency. `reportlab` will be removed.

---

## Scope

Three files, no interface changes. `@register("pdf")`, `ParseResult`, and `Exporter` are unchanged, so `import_router.py`, `export_router.py`, and all service code remain untouched.

---

## Architecture

```
PDF bytes → PdfParser.parse()
              ├─ Tier 1: pdfplumber  (word-level + tables)  always runs first
              ├─ Tier 2: pymupdf     (span dict → word model)  if total_chars < 50
              ├─ Tier 3: pytesseract (OCR via pdf2image)       if total_chars < 100
              └─ → TierResult(text, words, tables, meta)
                    ↓
              _heuristic_parse(words, tables, text)
                    → baseline Profile  (always succeeds offline)
                    ↓
              _ai_refine(text)             [optional, gated on quality threshold]
                    → ai_dict or None
                    ↓
              _merge_ai(baseline, ai_dict) [conservative, deterministic rules]
                    → final Profile
                    ↓
              ParseResult(profile, warnings)

Profile → PdfExporter.export()
              └─ FPDF() from fpdf2
                    → _section_title(), _body_line(), _bullet(), _job_meta() helpers
                    → bytes
```

---

## `pdf_parser.py` — Full Design

### Tier result shape

```python
@dataclass
class TierResult:
    text: str
    words: list[dict]      # unified word model (see below)
    tables: list[list]     # list of extracted tables (list of rows, each row a list of str)
    tier: int              # 1, 2, or 3
    meta: dict             # {"page_count": int, "page_chars": [int, ...], "tier_name": str}
```

All three extraction functions return a `TierResult`. This shape is stable for future Approach C migration (per-page tier selection) without redesigning call sites.

### Unified word model

Every word dict must have at minimum:
```python
{"text": str, "x0": float, "top": float, "size": float, "fontname": str}
```

- **Tier 1 (pdfplumber):** `page.extract_words(extra_attrs=["size", "fontname"])` already returns this shape.
- **Tier 2 (pymupdf):** `page.get_text("dict")` returns `blocks → lines → spans`. Normalize each span into the word model by splitting on whitespace. Use span `"size"` and `"font"` fields. Accumulate per-page chars for `meta["page_chars"]`.
- **Tier 3 (pytesseract):** returns plain text only; set `words=[]` and `tables=[]`. Section detection falls back to keyword-only matching when word list is empty.

### Extraction functions

```python
def _extract_tier1(data: bytes) -> TierResult: ...
def _extract_tier2(data: bytes) -> TierResult: ...
def _extract_tier3(data: bytes) -> TierResult: ...

def _pick_tier(data: bytes) -> TierResult:
    r = _extract_tier1(data)
    if len(r.text) < 50:
        r = _extract_tier2(data)
    if len(r.text) < 100:
        r = _extract_tier3(data)
    return r  # warnings include: "Extracted via Tier N (pdfplumber/pymupdf/OCR)"
```

Each function wraps all library calls in try/except; on failure it returns a `TierResult` with empty text and a warning, never raises.

### Section detection

```python
def _detect_sections(words: list[dict], text: str) -> list[tuple[int, str]]:
    ...
```

Returns `[(line_index, section_name), ...]` sorted by document order.

- When `words` is non-empty: a line is a header candidate if its max word size `>= 11.5` **AND** its normalized text matches `_SECTION_MAP`. Font size is the primary signal; keyword match is required to avoid treating every large font as a section header.
- When `words` is empty (Tier 3 OCR path): fall back to pure `_SECTION_MAP` keyword matching on lines, same as current behavior.
- Strips separator characters `: – — _ •` before lookup, same as current `_is_section_header`.

### Heuristic parse

```python
def _heuristic_parse(words: list[dict], tables: list[list], text: str) -> Profile:
    ...
```

- **Name detection:** Find the word cluster with the largest median font size in the top 20% of first-page vertical extent, filter out `_SECTION_MAP` matches and contact-pattern matches. Fall back to first non-contact line if no cluster qualifies.
- **Contact:** regex scan of first 10 lines (email, phone, URL — unchanged from current).
- **Skills:** First check `tables` — if any extracted table has cells that look like skill strings (length 2–40, no date pattern), flatten them into `Skill` objects. Then fall back to line-by-line delimiter logic for non-table skills.
- **Experience, Projects, Education, Certifications:** Same heuristic logic as current, but operating on coordinate-segmented text blocks rather than raw lines. Date extraction and bullet detection unchanged.
- **Summary:** Unchanged accumulation of lines under the summary section.

### AI refinement

```python
def _ai_refine(text: str) -> dict | None:
    ...
```

**Gate condition:** only run if `len(text) >= 200` AND `complete_simple` is importable AND AI is configured. Return `None` immediately otherwise.

The prompt instructs the model to return a JSON object with the same schema as the current prompt, but prefaced with: *"The following resume text has already been parsed. Return a corrected and normalized version. Do not invent data not present in the text."*

Wrapped in try/except; returns `None` on any failure.

### Conservative merge

```python
def _merge_ai(baseline: Profile, ai_dict: dict) -> Profile:
    ...
```

Explicit rules — no fuzzy logic:

| Field | Rule |
|---|---|
| `full_name`, `email`, `phone` | Never overwrite if baseline value is non-empty |
| `location` | Overwrite only if baseline is empty |
| `summary` | Overwrite if AI output is non-empty and longer than baseline |
| `skills` | Replace baseline list if AI list is non-empty and longer; otherwise keep baseline |
| `experience` | Append AI entries whose company+role pair is not already in baseline; never remove baseline entries |
| `projects[].description` | Overwrite per-project if AI description is non-empty and longer than baseline |
| `education`, `certifications` | Append AI entries not already in baseline by name match; never remove |
| `availability`, `compensation` | Never overwrite if baseline is non-empty |

If `ai_dict` is `None`, malformed JSON, or missing `full_name`, skip merge entirely and append `"AI refinement skipped"` warning.

---

## `pdf_exporter.py` — Full Design

### Unicode font

Bundle `DejaVuSans.ttf` and `DejaVuSans-Bold.ttf` (public domain) into `backend/assets/fonts/`. On `PdfExporter.__init__`, call `pdf.add_font("DejaVu", style="", fname=<path>)` and `pdf.add_font("DejaVu", style="B", fname=<path>)`. If the font file is missing, raise `FileNotFoundError` with a clear message — no silent Latin-1 fallback.

### Helper methods

```python
class PdfExporter(Exporter):
    mime_type = "application/pdf"
    extension = "pdf"

    # Internal helpers — each calls set_font/set_text_color then writes one unit of content
    def _section_title(self, pdf: FPDF, title: str) -> None: ...   # rule + bold uppercase header
    def _body_line(self, pdf: FPDF, text: str) -> None: ...        # 9pt dark body multi_cell
    def _bullet(self, pdf: FPDF, text: str) -> None: ...           # 9pt dark, 5mm left indent
    def _job_meta(self, pdf: FPDF, text: str) -> None: ...         # 8.5pt italic slate

    def export(self, profile: Profile) -> bytes: ...
```

### Color scheme (unchanged)

| Token | Hex | Use |
|---|---|---|
| BLUE | `#1e3a8a` | Name, section headers, HR rule |
| SLATE | `#475569` | Contact line, job meta |
| DARK | `#0f172a` | Body text, bullets |

### Page setup

```python
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=19)
pdf.add_page()
pdf.set_margins(19, 19, 19)  # ~0.75 inch
```

### Section order (unchanged)

name → contact → summary → skills → experience → projects → education → certifications → availability/compensation

Skills render as `"Python (3y) • Docker (2y) • ..."` using `multi_cell` for wrapping.
Experience bullets use `_bullet()` with `• ` prefix.

---

## `requirements.txt` — Changes

### Remove
- `pypdfium2==5.9.0` — unused, 15 MB native binary
- `pdfminer.six==20251230` — transitive dep of pdfplumber; let pdfplumber manage it
- `reportlab==4.5.1` — replaced by fpdf2

### Add
- `pymupdf>=1.24.0` — Tier 2 PDF fallback parser
- `pytesseract>=0.3.13` — Tier 3 OCR
- `pdf2image>=1.17.0` — PDF → PIL images for OCR
- `fpdf2>=2.8.0` — PDF export
- `python-magic>=0.4.27` — file type detection by binary signature
- `slowapi>=0.1.9` — rate limiting for AI endpoints

### Keep unchanged
`pdfplumber==0.11.9`, `pillow==12.2.0`, `python-docx==1.2.0`, `lxml==6.1.1`, full FastAPI/SQLModel/pydantic stack.

---

## Error handling contract

- Every library call that touches external file data is wrapped in try/except.
- Errors append a human-readable string to `ParseResult.warnings` — they never raise.
- The only exception: `PdfExporter` raises `FileNotFoundError` if the bundled TTF is missing, because that is a deployment error, not a user data error.
- All modules use `logger = get_logger(__name__)` for debug/info/warning logging.

---

## What is explicitly out of scope

- No changes to `import_router.py`, `export_router.py`, or any other file.
- No per-page tier selection (Approach C — planned future upgrade).
- No changes to `ai_service.py` or `complete_simple()`.
- `python-magic` and `slowapi` are added to `requirements.txt` only; wiring them into routers is a separate task.
- No new tests in this spec (test additions are a follow-up task).
