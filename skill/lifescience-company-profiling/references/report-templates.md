# Company Profiling - Report Templates

## Overview

This document provides standardized report templates for the Company Profiling skill (lifescience-company-profiling. All reports must follow these templates to ensure consistency, quality, and completeness.

---

## Template 1: Fast-Track Company Profile (Default)

**Use When:** User asks for quick overview or initial company understanding
**Token Budget:** ~500 tokens
**PATHs Executed:** PATH 1 + PATH 2 (quick overview)

### Template Structure

```markdown
# {Company Name} - Company Profile

**Core Conclusions:**
- [1-3 bullet points of key findings]
- [Pipeline overview]
- [Key strengths/strategic focus]

---

## Company Overview

| Attribute | Value |
|:---|:---|
| Company | {Company Name} |
| Headquarters | {Location} |
| Founded | {Year} |
| Market Cap | {Value} |
| Key Focus Areas | {Therapeutic areas} |
| Technology Platforms | {Platforms} |

## Pipeline Summary

| Stage | Count | Key Assets |
|:---|:---|:---|
| Approved | {X} | {Top 2-3} |
| Phase 3 | {X} | {Top 2-3} |
| Phase 2 | {X} | {Top 2-3} |
| Phase 1 | {X} | {Top 2-3} |

## Strategic Focus

{2-3 paragraphs on company strategy}
- Therapeutic area focus
- Technology differentiation
- Business development approach

## Key Strengths

{1-2 paragraphs on competitive advantages}

---

**For deeper analysis available:**
- [ ] Detailed patent FTO risk assessment
- [ ] Deal financial analysis and valuation
- [ ] Technology platform comparison with competitors

For target-specific competitive analysis → Reply "target" to switch to Target Intelligence
For specific drug characteristics → Reply "drug" to switch to Pharmaceuticals Exploration
```

### Example Output

```markdown
# AstraZeneca - Company Profile

**Core Conclusions:**
- AstraZeneca maintains a leading oncology franchise with ~40 pipeline assets, anchored by Enhertu (HER2 ADC) partnership with Daiichi Sankyo and novel TROP2 ADC (datopotamab deruxtecan)
- Respiratory/Vaccine leadership strengthened post-COVID with Synagis replacement and next-gen mRNA vaccines; Cardiovascular portfolio led by Farxiga (SGLT2) expansion into CKD/HF
- Management guidance reflects confidence in ~20% CAGR through 2025, supported by 10+ Phase 3 readouts expected

---

## Company Overview

| Attribute | Value |
|:---|:---|
| Company | AstraZeneca PLC |
| Headquarters | Cambridge, UK |
| Founded | 1999 (Merger of Astra AB + Zeneca Group) |
| Market Cap | ~$220B |
| Key Focus Areas | Oncology, Cardiovascular, Respiratory, Immunology |
| Technology Platforms | ADC, mRNA, Bispecifics, Small molecules |

## Pipeline Summary

| Stage | Count | Key Assets |
|:---|:---|:---|
| Approved | ~30 | Enhertu, Imjudo, Tagrisso, Lynparza, Farxiga, Symbicort |
| Phase 3 | ~15 | Datopotamab deruxtecan, Ceralasertib, AZD5305, Tezepelumab expansion |
| Phase 2 | ~20 | Novel ADC pipeline, Anti-TIGIT, Anti-CTLA-4 combinations |
| Phase 1 | ~10 | Next-gen ADC, Novel immunology targets |

## Strategic Focus

AstraZeneca has strategically positioned itself as the leader in Antibody Drug Conjugates (ADC) through the transformative Enhertu partnership, with a robust TROP2 ADC in Phase 3. The oncology franchise spans multiple modalities including small molecules (Tagrisso, Lynparza), immunotherapy (Imjudo), and next-gen combinations (PARP + PD-L1). Outside oncology, Farxiga's expansion into cardiorenal indications represents a $5B+ franchise opportunity, while the respiratory franchise targets long-term replacement therapies.

## Key Strengths

AstraZeneca's differentiated technology platforms (ADC, mRNA, bispecifics) enable modality-agnostic drug development. The company's global clinical trial network supports rapid Phase 1-3 execution, while the Daiichi Sankyo partnership provides proven co-development and commercialization capability. Strong late-stage pipeline with 15+ Phase 3 assets positions the company for sustained growth through 2030.

---

**For deeper analysis available:**
- [ ] Detailed patent FTO risk assessment
- [ ] Deal financial analysis and valuation
- [ ] Technology platform comparison with competitors

For target-specific competitive analysis → Reply "target" to switch to Target Intelligence
For specific drug characteristics → Reply "drug" to switch to Pharmaceuticals Exploration
```

---

## Template 2: Comprehensive Company Report (Deep-Dive)

**Use When:** User requests comprehensive analysis or detailed investigation
**Token Budget:** ~1800 tokens
**PATHs Executed:** All paths based on query type

### Template Structure

```markdown
# {Company Name} - Comprehensive Company Analysis

**Core Conclusions:**
- [3-5 bullet points covering key characteristics]
- [Pipeline highlights]
- [Patent strategy]
- [Deal activity]
- [Investment positioning]

---

## Section I: Company Overview

### 1.1 Basic Information

| Attribute | Value |
|:---|:---|
| Company Name | {Full name} |
| Ticker Symbol | {Symbol} |
| Headquarters | {Location} |
| Founded | {Year} |
| Employees | {Count} |
| Market Cap | {Value} |
| Annual Revenue | {Value} |
| R&D Budget | {Value} |

### 1.2 Business Overview

{Company history, key milestones, current business structure}

### 1.3 Technology Platforms

| Platform | Description | Key Assets |
|:---|:---|:---|
| {Platform 1} | {Description} | {Assets} |
| {Platform 2} | {Description} | {Assets} |

### 1.4 Financial Position

| Metric | FY2023 | FY2024 | Growth |
|:---|:---|:---|:---|
| Revenue | ${X}B | ${X}B | {X}% |
| R&D Spend | ${X}B | ${X}B | {X}% |
| Net Income | ${X}B | ${X}B | {X}% |

---

## Section II: R&D Pipeline Analysis

### 2.1 Pipeline Overview

| Development Stage | Count | % of Pipeline |
|:---|:---|:---|
| Approved | {X} | {X}% |
| Phase 3 | {X} | {X}% |
| Phase 2 | {X} | {X}% |
| Phase 1 | {X} | {X}% |
| Preclinical | {X} | {X}% |

### 2.2 Pipeline by Therapeutic Area

| Therapeutic Area | Approved | Phase 3 | Phase 2 | Phase 1 |
|:---|:---|:---|:---|:---|
| {TA 1} | {X} | {X} | {X} | {X} |
| {TA 2} | {X} | {X} | {X} | {X} |

### 2.3 Key Pipeline Assets

| Drug/Asset | Drug_type | Indication | Phase | Mechanism | Key Milestone | Competitive Position |
|:---|:---|:---|:---|:---|:---|:---|
| {Asset 1} | {Drug_type} | {Indication} | Phase X | {Mechanism} | {Milestone} | {Position} |
| {Asset 2} | {Drug_type} | {Indication} | Phase X | {Mechanism} | {Milestone} | {Position} |

### 2.4 Late-Stage Asset Details

#### {Asset Name}

| Parameter | Value |
|:---|:---|
| Indication | {Indication} |
| Mechanism | {Mechanism} |
| Phase | Phase X |
| Key Trial | {NCT} |
| Expected Readout | {Timeline} |
| Target Population | {Population} |

**Clinical Data:** {Summary of existing data}
**Competition:** {Key competitors}

### 2.5 Highlight & Risk Assessment

#### Strengths
- [Strength 1]
- [Strength 2]

#### Risks
- [Risk 1]
- [Risk 2]

---

## Section III: Patent Landscape

### 3.1 Patent Portfolio Overview

| Metric | Value |
|:---|:---|
| Total Patents | {Count} |
| Key Patent Families | {Count} |
| FTO Coverage | {Assessment} |

### 3.2 Patent by Technology

| Technology | Patent Count | Key Families | Expiration Focus |
|:---|:---|:---|:---|
| {Technology 1} | {Count} | {Families} | {Year range} |
| {Technology 2} | {Count} | {Families} | {Year range} |

### 3.3 Core Patent Protection

| Asset | Patent Family | Coverage | Expiration | FTO Risk |
|:---|:---|:---|:---|:---|
| {Asset} | {Family} | {Coverage} | {Year} | {Risk level} |

### 3.4 FTO Risk Assessment

| Risk Category | Assessment | Mitigation Strategy |
|:---|:---|:---|
| Platform patents | {Assessment} | {Strategy} |
| Lead compounds | {Assessment} | {Strategy} |
| Formulations | {Assessment} | {Strategy} |

### 3.5 Technology Direction

{Description of patent filing trends, emerging technology protection}

---

## Section IV: Deals & Collaborations

### 4.1 Deal Summary

| Deal Type | Count (2022-2024) | Total Value | Strategic Focus |
|:---|:---|:---|:---|
| Licensing (in) | {X} | ${X}B | {Focus} |
| Licensing (out) | {X} | ${X}B | {Focus} |
| Collaboration | {X} | ${X}B | {Focus} |
| Acquisition | {X} | ${X}B | {Focus} |

### 4.2 Notable Recent Deals

| Deal Type | Partner | Asset | Deal Value | Date | Strategic Rationale |
|:---|:---|:---|:---|:---|:---|
| {Type} | {Company} | {Asset} | {Value} | {Date} | {Rationale} |
| {Type} | {Company} | {Asset} | {Value} | {Date} | {Rationale} |

### 4.3 Partnership Strategy

{Description of deal-making philosophy, preferred deal structures}

### 4.4 Notable Historical Deals

| Deal | Year | Partner | Asset | Outcome |
|:---|:---|:---|:---|:---|
| {Deal} | {Year} | {Partner} | {Asset} | {Outcome} |

---

## Section V: Investment/Collaboration Assessment

### 5.1 Overall Assessment

| Dimension | Assessment | Confidence | Key Drivers | Risk Factors |
|:---|:---|:---|:---|:---|
| Pipeline Strength | Strong/Medium/Weak | High/Medium/Low | {Drivers} | {Risks} |
| Financial Health | Stable/Growing/Challenged | High/Medium/Low | {Drivers} | {Risks} |
| Market Position | Leader/Challenger/Niche | High/Medium/Low | {Drivers} | {Risks} |
| Deal Activity | High/Moderate/Low | High/Medium/Low | {Drivers} | {Risks} |

### 5.2 Valuation Analysis

| Metric | Value | Benchmark | Assessment |
|:---|:---|:---|:---|
| Market Cap | {Value} | - | - |
| P/E Ratio | {X}x | {X}x sector avg | {Assessment} |
| EV/Revenue | {X}x | {X}x sector avg | {Assessment} |
| Pipeline NPV | {Value} | - | {Assessment} |

### 5.3 Investment Highlights

1. [Highlight 1]
2. [Highlight 2]
3. [Highlight 3]

### 5.4 Investment Concerns

1. [Concern 1]
2. [Concern 2]
3. [Concern 3]

### 5.5 Collaboration Opportunity Assessment

| Factor | Assessment | Notes |
|:---|:---|:---|
| Strategic Fit | {High/Medium/Low} | {Notes} |
| Technology Complementarity | {High/Medium/Low} | {Notes} |
| Deal Terms | {Favorable/Neutral/Unfavorable} | {Notes} |

---

## Section VI: Conclusion

### 6.1 Company Assessment Summary

{2-3 paragraphs summarizing company positioning, strategy, outlook}

### 6.2 Competitive Positioning

{Assessment vs key competitors in focus areas}

### 6.3 Future Outlook

{Predicted evolution, upcoming catalysts, strategic direction}

### 6.4 Recommendations

{If applicable - recommendations for investors, partners, or other stakeholders}

---

## Key References

- SEC Filings: {10-K, 10-Q citations}
- Clinical Trials: {NCT numbers}
- Company Disclosures: {Press release citations}

---

**Assessment Level:** Evidence-based analysis based on [Level A/B/C] sources
```

---

## Template 3: Pipeline-Focused Report

**Use When:** User specifically asks about company pipeline, drug candidates, development strategy
**Token Budget:** ~1000 tokens
**PATHs Executed:** PATH 2 + PATH 1 (basic info)

### Template Structure

```markdown
# {Company Name} - Pipeline Analysis

**Core Conclusions:**
- [Pipeline summary bullet points]
- [Stage distribution]
- [Key assets highlights]

---

## Pipeline Overview

| Development Stage | Count | Therapeutic Focus |
|:---|:---|:---|
| Approved | {X} | {Areas} |
| Phase 3 | {X} | {Areas} |
| Phase 2 | {X} | {Areas} |
| Phase 1 | {X} | {Areas} |
| Preclinical | {X} | {Areas} |

## Key Assets by Phase

### Phase 3 Assets

| Asset | Drug_type | Indication | Mechanism | Key Milestone | Expected Readout |
|:---|:---|:---|:---|:---|:---|:---|
| {Asset} | {Drug_type} | {Indication} | {Mechanism} | {Milestone} | {Timeline} |

### Phase 2 Assets

| Asset | Drug_type | Indication | Mechanism | Key Milestone |
|:---|:---|:---|:---|:---|:---|
| {Asset} | {Drug_type} | {Indication} | {Mechanism} | {Milestone} |

### Phase 1 Assets

| Asset | Drug_type | Indication | Mechanism | Next Steps |
|:---|:---|:---|:---|:---|
| {Asset} | {Drug_type} | {Indication} | {Mechanism} | {Next steps} |

## Pipeline by Therapeutic Area

| Therapeutic Area | Phase 3 | Phase 2 | Phase 1 | Approved |
|:---|:---|:---|:---|:---|
| {TA 1} | {X} | {X} | {X} | {X} |
| {TA 2} | {X} | {X} | {X} | {X} |

## Pipeline by Modality

| Modality | Count | Key Examples |
|:---|:---|:---|
| {Modality 1} | {X} | {Examples} |
| {Modality 2} | {X} | {Examples} |

## Upcoming Catalysts

| Date | Catalyst | Asset | Impact |
|:---|:---|:---|:---|
| {Timeline} | {Catalyst} | {Asset} | {Impact} |

## Competitive Assessment

{Assessment of pipeline vs key competitors in each therapeutic area}

---

*Pipeline data from company disclosures and ClinicalTrials.gov [Level B/C sources]*
```

---

## Template 4: Deal Intelligence Report

**Use When:** User asks about company BD strategy, licensing deals, M&A activity
**Token Budget:** ~800 tokens
**PATHs Executed:** PATH 4 + PATH 1 (basic context)

### Template Structure

```markdown
# {Company Name} - Deal Intelligence Analysis

**Core Conclusions:**
- [Deal activity summary bullet points]
- [Strategic priorities]
- [Key transaction highlights]

---

## Deal Activity Overview

| Metric | 2022 | 2023 | 2024 | Trend |
|:---|:---|:---|:---|:---|
| Total Deals | {X} | {X} | {X} | {Trend} |
| Licensing (in) | {X} | {X} | {X} | {Trend} |
| Licensing (out) | {X} | {X} | {X} | {Trend} |
| Collaborations | {X} | {X} | {X} | {Trend} |
| Acquisitions | {X} | {X} | {X} | {Trend} |
| Total Deal Value | ${X}B | ${X}B | ${X}B | {Trend} |

## Strategic Deal Priorities

{Description of deal-making strategy, focus areas, preferred structures}

## Notable Recent Deals

### Deal 1: {Deal Name}

| Parameter | Value |
|:---|:---|
| Deal Type | {Type} |
| Partner | {Company} |
| Asset | {Asset/Technology} |
| Deal Value | {Value} |
| Upfront | {Value} |
| Milestones | {Value} |
| Royalties | {X}% |
| Date | {Date} |

**Strategic Rationale:** {Description}
**Deal Highlights:** {Key terms}

### Deal 2: {Deal Name}

{Same structure}

## Deal Financing Structure

| Structure | Frequency | Typical Terms |
|:---|:---|:---|
| {Structure} | {Frequency} | {Terms} |

## Partnership Ecosystem

| Partner Type | Key Partners | Focus |
|:---|:---|:---|
| {Type} | {Companies} | {Focus} |

## Deal Track Record

| Historical Deal | Year | Partner | Outcome |
|:---|:---|:---|:---|
| {Deal} | {Year} | {Partner} | {Outcome} |

## BD Team Assessment

{Assessment of deal-making capability, track record, strategic vision}

## Recommendations

{If applicable - recommendations for potential partners or deal evaluation}

---

*Deal data from company disclosures and industry reports [Level B/C sources]*
```

---

## Template 5: Patent Strategy Report

**Use When:** User asks about company patent portfolio, FTO risks, IP strategy
**Token Budget:** ~800 tokens
**PATHs Executed:** PATH 3 + PATH 1 (basic context)

### Template Structure

```markdown
# {Company Name} - Patent Strategy Analysis

**Core Conclusions:**
- [Patent strategy summary bullet points]
- [Portfolio highlights]
- [FTO risk assessment]

---

## Patent Portfolio Overview

| Metric | Value |
|:---|:---|
| Total Active Patents | {Count} |
| Key Patent Families | {Count} |
| Geographic Coverage | {Regions} |
| Filing Trend (2020-2024) | {Trend} |

## Portfolio by Technology

| Technology | Patent Count | Key Families | Expiration Focus |
|:---|:---|:---|:---|
| {Technology 1} | {Count} | {Count} | {Year range} |
| {Technology 2} | {Count} | {Count} | {Year range} |
| {Technology 3} | {Count} | {Count} | {Year range} |

## Key Patent Family Analysis

### Family 1: {Platform/Asset}

| Parameter | Value |
|:---|:---|
| Patent Family | {Family ID} |
| Coverage | {Composition/Method/Use} |
| Geographic Scope | {Regions} |
| Expiration | {Year} |
| FTO Assessment | {Risk level} |

**Description:** {Description}

### Family 2: {Platform/Asset}

{Same structure}

## FTO Risk Assessment

| Risk Category | Assets Affected | Risk Level | Mitigation |
|:---|:---|:---|:---|
| Platform patents | {Assets} | {Low/Medium/High} | {Strategy} |
| Lead compounds | {Assets} | {Low/Medium/High} | {Strategy} |
| Formulation | {Assets} | {Low/Medium/High} | {Strategy} |

## Composition of Matter Coverage

| Asset | Composition Patent | Expiration | FTO Risk |
|:---|:---|:---|:---|
| {Asset} | {Patent} | {Year} | {Risk} |

## Method of Treatment Coverage

| Indication | Method Patent | Expiration | FTO Risk |
|:---|:---|:---|:---|
| {Indication} | {Patent} | {Year} | {Risk} |

## Formulation & Delivery Patents

| Patent Type | Count | Key Coverage | Expiration |
|:---|:---|:---|:---|
| {Type} | {Count} | {Coverage} | {Range} |

## Patent Filing Trends

{Description of recent filing patterns, emerging technology protection}

## Generic/Biosimilar Risk Assessment

| Asset | Patent Cliff | Generic Competition | Timeline |
|:---|:---|:---|:---|
| {Asset} | {Yes/No} | {Assessment} | {Timeline} |

## IP Strategy Assessment

{Overall assessment of patent strategy, coverage gaps, recommendations}

---

*Patent data from USPTO, EPO, and company disclosures [Level B/C sources]*
```

---

## Quality Checklist

Before finalizing any report, verify:

- [ ] Company name and identifiers correctly identified
- [ ] Pipeline summary includes phase, mechanism, indication, key milestones
- [ ] Patent portfolio summary includes FTO risk assessment
- [ ] Deal summary includes deal value, strategic rationale
- [ ] Investment assessment includes pipeline strength, financial health, market position
- [ ] All data cited with source and evidence level
- [ ] No target-specific competitive analysis
- [ ] No drug-specific characteristics (delegate to Pharmaceuticals Exploration if needed)
- [ ] Evidence hierarchy applied to all data citations
- [ ] Conclusion provides actionable company assessment
- [ ] Followed correct template for report type
- [ ] Token budget appropriate for mode
