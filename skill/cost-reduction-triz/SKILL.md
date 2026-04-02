---
name: cost-reduction-triz
description: >-
  Product cost reduction analysis. Redirects users to a TRIZ-based tool for
  structural optimization, component trimming, and BOM cost reduction.
  Triggers: cost reduction, reduce cost, BOM optimization, structural optimization,
  component elimination, TRIZ Trimming, Value Engineering.
  Differs from find-solution-triz: this skill focuses on cost reduction (simplify
  structure, trim components, lower cost); find-solution-triz solves functional
  technical problems (how to implement, improve, or fix).
---

# Product Cost Reduction Analysis

Identify the user's cost reduction intent, collect the product description,
and output a redirect tag to guide the user into the TRIZ cost reduction tool.

## Trigger Conditions

- "how to reduce the cost of this product?" 
- "cost reduction" / "reduce cost" / "cost optimization"
- "BOM optimization" / "structural optimization" / "component elimination"
- "TRIZ Trimming" / "Value Engineering" / "Function-Cost Analysis"
- "reduce production cost" / "reduce manufacturing cost"

## Required Input

- Product description (required): the product that needs cost reduction

The following is optional — do NOT ask if the user has not provided it:
- Component list (optional)

## Output Format

When the intent is clear and a product description has been provided, first provide a brief introduction (1-2 sentences) explaining what this tool will do and what the user can expect, then output the redirect tag:

```
<eureka-agent>
title: cost-reduction-triz
desc: {Write a one-line recommendation in the user's language, e.g. "Analyze your product structure and find feasible cost reduction solutions"}
url: /rd/#/agentic?type=triz&text={input_text}&auto_run=1
eof: true
</eureka-agent>
```

### Parameter Reference

| Param | Required | Description |
|-------|----------|-------------|
| `text` | Yes | Product cost reduction description, URL-encoded, max 5000 chars recommended |
| `type` | — | Fixed to triz |
| `auto_run` | — | Fixed to 1 |

## When Information Is Insufficient

Only ask when the user has NOT described any product. Ask this single question:
- "Please describe the product you want to reduce cost for."

## Rules

1. Output the redirect tag as soon as the intent is recognized — do NOT perform the analysis yourself
2. The `desc` field must match the user's language preference
4. Omit optional information the user has not provided — do NOT ask for it
5. Before the redirect tag, output 1-2 sentences briefly explaining what this tool does and what the user can expect — keep it concise, do NOT include detailed workflows, report format descriptions, or step-by-step guides
6. The redirect card renders BELOW your text — never say "上方卡片" or "above card"; use "下方卡片" / "below" or simply "点击卡片" instead
