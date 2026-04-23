# Lifescience Company Profiling - Search Reference

## Pharma Intelligence MCP Server

**MCP Server ID**: `245f3ce8-79e4-4c2a-927c-e155c293f097`
**URL**: https://open.patsnap.com/marketplace/mcp-servers/245f3ce8-79e4-4c2a-927c-e155c293f097

This skill focuses on **company-level intelligence** - NOT drug characteristics or competitive landscape of specific targets.

---

## PATH 1: Basic Company Information

```python
ls_company_search(
    company=["company_name"],
    limit=10
)

ls_company_fetch(
    company_ids=["company-uuid-1"]
)

ls_paper_search(
    company=["company_name"],
    key_word=["company profile", "history", "leadership", "technology platform"],
    limit=20
)
```

---

## PATH 2: R&D Pipeline Analysis

### Full Pipeline Search

```python
ls_drug_search(
    company=["company_name"],
    limit=50
)
```

### Pipeline by Stage

```python
ls_drug_search(
    company=["company_name"],
    development_status=["approved", "phase_3", "phase_2", "phase_1"],
    limit=50
)
```

### Pipeline by Therapeutic Area

```python
ls_drug_search(
    company=["company_name"],
    indication=["oncology", "immunology", "cardiovascular"],
    limit=30
)
```

### Pipeline by Modality

```python
ls_drug_search(
    company=["company_name"],
    drug_type=["small molecule", "monoclonal antibody", "ADC", "gene therapy", "mRNA"],
    limit=30
)
```

### Pipeline by Target

```python
ls_drug_search(
    company=["company_name"],
    target=["target_name"],
    limit=20
)
```

### Clinical Trials

```python
ls_clinical_trial_search(
    company=["company_name"],
    phase=["phase_3", "phase_2"],
    limit=30
)
```

---

## PATH 3: Patent Analysis

### Company Patent Portfolio

```python
ls_patent_search(
    company=["company_name"],
    limit=50
)
```

### Patent by Technology

```python
ls_patent_search(
    company=["company_name"],
    key_word=["bispecific", "CAR-T", "gene therapy", "ADC", "platform"],
    limit=30
)
```

### Patent Details

```python
ls_patent_fetch(
    patent_ids=["patent-uuid-1"]
)
```

### Patent by Type

```python
# Composition of matter
ls_patent_search(
    company=["company_name"],
    key_word=["composition of matter", "compound"],
    limit=30
)

# Formulation
ls_patent_search(
    company=["company_name"],
    key_word=["formulation", "delivery"],
    limit=20
)

# Method of treatment
ls_patent_search(
    company=["company_name"],
    key_word=["method of treatment", "use patent"],
    limit=20
)
```

---

## PATH 4: Deals & Collaborations

### Full Deal History

```python
ls_drug_deal_search(
    company=["company_name"],
    limit=50
)
```

### Deal by Type

```python
ls_drug_deal_search(
    company=["company_name"],
    deal_type=["licensing", "acquisition", "collaboration"],
    limit=30
)
```

### Deal by Date Range

```python
ls_drug_deal_search(
    company=["company_name"],
    deal_date_from="2020-01-01",
    deal_date_to="2024-12-31",
    limit=30
)
```

### Deal Direction

```python
# In-licensing
ls_drug_deal_search(
    company=["company_name"],
    deal_type=["licensing"],
    deal_direction=["in-licensing"],
    limit=20
)

# Out-licensing
ls_drug_deal_search(
    company=["company_name"],
    deal_type=["licensing"],
    deal_direction=["out-licensing"],
    limit=20
)

# M&A
ls_drug_deal_search(
    company=["company_name"],
    deal_type=["acquisition"],
    limit=20
)
```

### Deal Details

```python
ls_drug_deal_fetch(
    drug_deal_ids=["deal-uuid-1"]
)
```

---

## Quick Reference: Typical Search Combinations

### Company Overview (All Paths)

```python
# 1. Company info
ls_company_search(company=["company_name"], limit=10)

# 2. Pipeline
ls_drug_search(company=["company_name"], limit=50)

# 3. Patents
ls_patent_search(company=["company_name"], limit=30)

# 4. Deals
ls_drug_deal_search(company=["company_name"], limit=30)

# 5. Clinical trials
ls_clinical_trial_search(company=["company_name"], phase=["phase_3"], limit=20)
```

### Late-Stage Pipeline Focus

```python
ls_drug_search(
    company=["company_name"],
    development_status=["approved", "phase_3"],
    limit=20
)

ls_clinical_trial_search(
    company=["company_name"],
    phase=["phase_3"],
    limit=20
)
```

### Technology Platform Assessment

```python
# Pipeline by modality
ls_drug_search(
    company=["company_name"],
    drug_type=["ADC", "bispecific", "mRNA"],
    limit=30
)

# Platform patents
ls_patent_search(
    company=["company_name"],
    key_word=["platform", "technology", "composition of matter"],
    limit=30
)

# Platform deals
ls_drug_deal_search(
    company=["company_name"],
    deal_type=["collaboration"],
    key_word=["platform", "technology access"],
    limit=20
)
```

---

## Quality Checklist

- [ ] Company name and identifiers correctly identified
- [ ] Pipeline summary includes phase, mechanism, indication, key milestones
- [ ] Patent portfolio summary includes FTO risk assessment
- [ ] Deal summary includes deal value, strategic rationale
- [ ] Investment assessment includes pipeline strength, financial health, market position
- [ ] All data cited with source and evidence level
- [ ] No target-specific competitive analysis
- [ ] No drug-specific characteristics
- [ ] Evidence hierarchy applied to all data citations
- [ ] Conclusion provides actionable company assessment
