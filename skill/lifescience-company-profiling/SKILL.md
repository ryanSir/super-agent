---
name: lifescience-company-profiling
description: |
  Comprehensive intelligence on pharma and biotech companies.
  Trigger when: the query names a pharmaceutical or biotech company as the primary subject and asks about company-level intelligence — R&D pipeline overview, BD deals and licensing activity, M&A history, strategic positioning, competitive standing in a therapeutic area, technology platforms, financing history, investment thesis, or company-level competitive analysis.
  Also triggers for: "what is X company's pipeline", "X company's strategy in oncology", "X company's recent deals", "X company's ADC portfolio", "X company's competitive position", "X company's technology platform", "X company's financing history", "is X company a good investment", "X company's key assets", "what therapeutic areas does X focus on", "X company's R&D spending", "X company's Phase 3 readouts", "X company's BD deal history".
  Zone 1 (Commercial Intelligence) — Tier P only. No open-source or predictive data.
  Key disambiguation: use this skill when the COMPANY is the primary subject. Use lifescience-target-intelligence when the TARGET is the primary subject. Use lifescience-deal-intelligence for deal structure/valuation analysis. Use lifescience-patent-intelligence for patent FTO/expiration analysis.
license: MIT
metadata:
  author: patsnap
  version: '2.0.0'
  domain: lifescience
---


# Company Profiling

**Zone 1 — Tier P only.** All data from Patsnap MCP tools exclusively.

## Role

Pharmaceutical industry strategy consultant focusing on company-level intelligence. Focus areas:
- Pipeline analysis: drug assets by stage, therapeutic area, mechanism
- Deal intelligence: licensing, partnerships, M&A activity
- Strategic assessment: competitive positioning, investment opportunities
- Catalyst calendar: upcoming binary events

---

## Data Collection

**Search → Fetch pattern is mandatory.**

| Step | Tool | Purpose |
|------|------|---------|
| 1 | `ls_organization_fetch` | Company identity, background, technology platforms |
| 2 | `ls_financial_report_vector_search` | Financial reports, revenue data, R&D spending (semantic search) |
| 3 | `ls_drug_search` → `ls_drug_fetch` | Pipeline assets by company |
| 4 | `ls_drug_deal_search` → `ls_drug_deal_fetch` | Licensing and partnerships |
| 5 | `ls_patent_search` → `ls_patent_fetch` | Patent portfolio |
| 6 | `ls_clinical_trial_search` → `ls_clinical_trial_fetch` | Clinical progress |
| 7 | `ls_clinical_trial_result_search` → `ls_clinical_trial_result_fetch` | Key trial outcomes |
| 8 | `ls_news_vector_search` → `ls_news_fetch` | Recent news and announcements |
| 9 | `ls_web_search` | Analyst commentary, peer comparisons (last resort) |

Execute only the steps relevant to the query.

---

## Analysis Framework

### Pipeline Analytics

**Phase Distribution**: Calculate % of pipeline by stage (Preclinical / Phase 1 / Phase 2 / Phase 3 / Approved). Back-heavy pipeline = near-term revenue risk; front-heavy = long development runway.

**Therapeutic Concentration**: Identify therapeutic areas representing >30% of pipeline — signals strategic focus and competitive exposure.

**Catalyst Calendar**: Map upcoming binary events:

| Event Type | Asset | Expected Timing | Significance |
|------------|-------|-----------------|--------------|
| Phase 3 data readout | Drug A | Q3 2025 | Primary endpoint OS |
| NDA/BLA submission | Drug B | Q1 2026 | First approval |
| PDUFA date | Drug C | Q4 2025 | Binary approval event |
| Phase 2 interim | Drug D | H2 2025 | Go/no-go decision |

**Risk Assessment per late-stage asset**:
- Clinical risk (endpoint achievement probability)
- Competitive risk (faster competitors, SoC evolution)
- Regulatory risk (pathway clarity, precedent)
- Commercial risk (market size, pricing, reimbursement)

**Peer Comparison**: Compare pipeline breadth, phase distribution, and therapeutic focus vs 2–3 peer companies.

---

## Output

No mandatory template. Structure to best answer the specific question. Typical sections for a full company profile:

1. Company overview (background, platforms, financing history)
2. R&D pipeline (assets by stage and indication)
3. Deal activity (recent licensing, partnerships, M&A)
4. Catalyst calendar (upcoming binary events)
5. Strategic assessment (competitive positioning, investment outlook)

For simple factual queries (e.g., "what is AstraZeneca's pipeline in oncology"), return a concise direct answer. A "simple factual query" is one that asks for a single specific data point (one number, one date, one status) — NOT an analysis, landscape, pipeline, or multi-entity query. When in doubt, produce the full structured output.

### Visual Output

Use templates from `references/artifact-templates.md`. Apply the three-layer model.

**Layer A** (top artifact — when pipeline has ≥3 assets):
- Metric row: total pipeline assets / Phase 3 or NDA assets / approved products / key TA focus
- Card grid grouped by stage: `已批准` → `Phase 3/NDA` → `Phase 2` → `Phase 1`
- Card line 1: `[Drug name] · [Modality]`; line 2: `[Indication] · [Key milestone or readout]`
- Card color by therapeutic area: Oncology → `badge-phase3` · CV/Metabolic → `badge-approved` · Immunology → `badge-phase2` · Rare/Other → `badge-early`
- Chip row: pipeline breakdown by therapeutic area
- Catalyst list: 2–3 upcoming binary events below grid
- If R&D spending data available: add bar chart (A2) for R&D spend trend

**Layer B** (markdown after artifact):
- Pipeline table: drug / indication / stage / modality / key milestone
- Deal activity table: date / partner / deal type / value / asset
- Catalyst calendar: event / asset / expected timing / significance
- Strategic assessment: competitive positioning, investment outlook paragraphs

**Layer C** (inline in Layer B prose):
- Stage progress strip (C1) when describing a specific asset's development status
- Proportion bar (C3) when showing pipeline composition by TA or stage
- Delta indicator (C5) when citing R&D spend growth or revenue change
- Region badge row (C4) when describing approval status across markets

**Single company financial analysis** → skip Layer A card grid; Layer B markdown only.
**Deal history only** → skip Layer A; Layer B deal table only.

---

## Related Analysis

| Topic | Skill |
|-------|-------|
| Specific drug ADMET, PK/PD, safety | `lifescience-pharmaceuticals-exploration` |
| Target competitive landscape | `lifescience-target-intelligence` |
| Disease treatment landscape | `lifescience-disease-investigation` |
| Patent FTO, expiration, litigation | `lifescience-patent-intelligence` |
| Regulatory pathway, approval | `lifescience-regulatory-analysis` |
| Market size, revenue | `lifescience-commercial-analysis` |

---

```yaml
skill_zone: 1
tier_policy: "P only"
version: "2.0.0"
parent_middleware: "lifescience-middleware"
```
---
### Drug Charts

**Output chart placeholders conditionally at the end of the report — no explanatory text, no intro or outro phrases.**

**Precondition**: Render any chart **only when the drug set is non-empty and data is available**. Skip all charts if no drugs are identified in the report.

#### Rule 1 — Bulls Eye Chart
Render the Bulls Eye chart **only when all conditions are met**:
1. Query intent maps to a **range of drugs** (not a specific named drug)
2. All drug_ids for that condition are fully retrieved — when calling drug search tool, the returned drug count equals the `total` count, confirming no drugs are missing
3. Drug count for the condition is **greater than 3**

- drug_ids: comma-separated list of all known drug ids (e.g. "drug_id_1,drug_id_2,drug_id_3")
- type: choose from `"org"` | `"target"` | `"disease"` | `"drug_type"` based on the grouping dimension

<h2>🎯 Bulls Eye Chart - [org/target/disease/drug_type value]</h2>
<ls_bulls_eye_chart drug_ids="xxx,xxx,..." type="xxx"/>

#### Rule 2 — Individual Timeline Charts
Render for **each drug individually** when:
1. Query points to a **specific named drug**, OR
2. Query intent maps to a **range of drugs** but drug count is **3 or fewer**

For each drug, output all three chart placeholders:
- Pick up to 3 drugs; skip if none
- Drug name and drug_id must be real and valid — do not use fabricated or placeholder values

<h2>⏱️ Milestone Timeline - [Drug Name]</h2>
<ls_drug_milestone_timeline drug_id="xxx"/>

<h2>⏱️ First Approval Timeline - [Drug Name]</h2>
<ls_drug_approval_timeline drug_id="xxx"/>

<h2>📊 Patent Landscape - [Drug Name]</h2>
<ls_drug_patent_layout durg_id="xxx"/>

<!-- Repeat the three charts above for each drug, up to 3 drugs total -->
