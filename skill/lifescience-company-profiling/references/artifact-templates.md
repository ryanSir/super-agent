---
name: artifact-templates
description: Shared HTML, SVG, and inline visual templates for all life science skills. Three layers — Layer A (top-level artifact), Layer B (markdown structure), Layer C (inline visuals embedded in prose). Skills specify only their section groupings, card content, and badge decisions.
type: reference
---

# Artifact Templates

Three-layer output model. Templates are organized by layer. Individual skills specify only their **section groupings**, **card content mapping**, and **badge color decisions** — all HTML/SVG/CSS comes from here.

---

## Layer A — Visual Summary Templates

Top-level HTML artifact. Always appears before Layer B markdown.

---

### A1. HTML Card Grid

Use for: drug pipeline, competitive landscape, company portfolio, market structure.

```html
<style>
.metrics { display: grid; grid-template-columns: repeat(4,1fr); gap:10px; margin-bottom:24px; }
.metric-card { background: var(--color-background-secondary); border-radius: var(--border-radius-md); padding:12px; }
.metric-val { font-size:22px; font-weight:500; color: var(--color-text-primary); }
.metric-label { font-size:11px; color: var(--color-text-secondary); margin-top:3px; }
.section-label { font-size:11px; font-weight:500; color: var(--color-text-secondary); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px; }
.card-grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(160px,1fr)); gap:8px; margin-bottom:20px; }
.card { background: var(--color-background-primary); border: 0.5px solid var(--color-border-tertiary); border-radius: var(--border-radius-lg); padding:10px 12px; }
.card-name { font-size:13px; font-weight:500; color: var(--color-text-primary); }
.card-meta { font-size:11px; color: var(--color-text-secondary); margin-top:3px; }
.badge { display:inline-block; font-size:10px; font-weight:500; padding:2px 7px; border-radius:4px; margin-top:5px; }
.badge-approved { background: var(--color-background-success); color: var(--color-text-success); }
.badge-phase3  { background: var(--color-background-info);    color: var(--color-text-info);    }
.badge-phase2  { background: var(--color-background-warning); color: var(--color-text-warning); }
.badge-early   { background: var(--color-background-secondary); color: var(--color-text-secondary); }
.chip-row { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:20px; }
.chip { font-size:12px; padding:4px 10px; border-radius:20px; border:0.5px solid var(--color-border-tertiary); color: var(--color-text-secondary); }
</style>

<div style="padding:1rem 0">
  <!-- Metric row -->
  <div class="metrics">
    <div class="metric-card"><div class="metric-val">[N]</div><div class="metric-label">[Label]</div></div>
    <div class="metric-card"><div class="metric-val">[N]</div><div class="metric-label">[Label]</div></div>
    <div class="metric-card"><div class="metric-val">[N]</div><div class="metric-label">[Label]</div></div>
    <div class="metric-card"><div class="metric-val">[N]</div><div class="metric-label">[Label]</div></div>
  </div>
  <!-- Section group (repeat per stage / category) -->
  <div class="section-label">[Stage or Category]</div>
  <div class="card-grid">
    <div class="card">
      <div class="card-name">[Entity Name]</div>
      <div class="card-meta">[Meta line 1]</div>
      <div class="card-meta">[Meta line 2]</div>
      <span class="badge badge-approved">已批准</span>
    </div>
  </div>
  <!-- Chip row: modality / TA / region distribution -->
  <div class="chip-row">
    <div class="chip">[Category] · [Count or %]</div>
  </div>
</div>
```

---

### A2. Bar Chart (time-series numeric data)

Use for: market size forecast, revenue trend, pipeline count by year.

```html
<div style="position:relative; width:100%; height:180px; margin-bottom:8px;">
  <canvas id="chart-[id]" role="img" aria-label="[Accessible description]">
    [Fallback text describing the data]
  </canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
(function() {
  const isDark = matchMedia('(prefers-color-scheme: dark)').matches;
  new Chart(document.getElementById('chart-[id]'), {
    type: 'bar',
    data: {
      labels: [/* year or category labels */],
      datasets: [{ label: '[Label]', data: [/* values */],
        backgroundColor: isDark ? 'rgba(55,138,221,0.5)' : 'rgba(55,138,221,0.35)',
        borderColor: '#378ADD', borderWidth: 1.5, borderRadius: 4 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: ctx => ' ' + ctx.parsed.y } } },
      scales: {
        x: { grid: { display: false }, ticks: { color: isDark ? '#9c9a92' : '#73726c', font: { size: 11 } } },
        y: { grid: { color: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' },
             ticks: { color: isDark ? '#9c9a92' : '#73726c', font: { size: 11 } }, beginAtZero: true }
      }
    }
  });
})();
</script>
```

---

### A3. SVG Timeline / Swim Lane

Use for: patent filing density by year, clinical milestone sequence, technology evolution.

```svg
<svg width="100%" viewBox="0 0 680 [height]" xmlns="http://www.w3.org/2000/svg"
     role="img" aria-label="[Accessible label]">
  <!-- Stage row -->
  <text x="40" y="[y]" font-size="11" fill="var(--color-text-secondary)" font-family="sans-serif">[Stage]</text>
  <line x1="40" y1="[y+6]" x2="640" y2="[y+6]" stroke="var(--color-border-tertiary)" stroke-width="0.5"/>
  <!-- Entity card -->
  <rect x="[x]" y="[y+12]" width="140" height="64" rx="8"
        fill="var(--color-background-info)" stroke="var(--color-border-secondary)" stroke-width="0.5"/>
  <text x="[cx]" y="[cy]" text-anchor="middle" font-size="13" font-weight="500"
        fill="var(--color-text-primary)" font-family="sans-serif">[Name]</text>
  <text x="[cx]" y="[cy+16]" text-anchor="middle" font-size="11"
        fill="var(--color-text-secondary)" font-family="sans-serif">[Company · Modality]</text>
  <text x="[cx]" y="[cy+30]" text-anchor="middle" font-size="10"
        fill="var(--color-text-secondary)" font-family="sans-serif">[Key data]</text>
  <!-- Timeline axis -->
  <line x1="60" y1="[axis_y]" x2="640" y2="[axis_y]" stroke="var(--color-border-secondary)" stroke-width="1"/>
  <text x="[tick_x]" y="[axis_y+14]" text-anchor="middle" font-size="10"
        fill="var(--color-text-secondary)" font-family="sans-serif">[Year]</text>
</svg>
```

---

## Layer C — Inline Visual Components

Small HTML snippets embedded inside Layer B markdown sections. Max height ~40px. Never replicate Layer A inside Layer B.

---

### C1. Stage Progress Strip

Use when: describing a drug's development stage in a paragraph. Replaces "currently in Phase 2".

```html
<span style="display:inline-flex; align-items:center; gap:3px; font-size:11px; vertical-align:middle; margin:0 4px;">
  <span style="padding:2px 7px; border-radius:3px; background:var(--color-background-secondary); color:var(--color-text-secondary);">临床前</span>
  <span style="color:var(--color-text-secondary);">›</span>
  <span style="padding:2px 7px; border-radius:3px; background:var(--color-background-secondary); color:var(--color-text-secondary);">Ph1</span>
  <span style="color:var(--color-text-secondary);">›</span>
  <span style="padding:2px 7px; border-radius:3px; background:var(--color-background-info); color:var(--color-text-info); font-weight:500;">Ph2 ◀</span>
  <span style="color:var(--color-text-secondary);">›</span>
  <span style="padding:2px 7px; border-radius:3px; background:var(--color-background-secondary); color:var(--color-text-secondary);">Ph3</span>
  <span style="color:var(--color-text-secondary);">›</span>
  <span style="padding:2px 7px; border-radius:3px; background:var(--color-background-secondary); color:var(--color-text-secondary);">已批准</span>
</span>
```

---

### C2. Score Gauge Bar

Use when: showing a validation score, confidence level, or GO/NO-GO dimension score inline.

```html
<span style="display:inline-flex; align-items:center; gap:6px; vertical-align:middle; margin:0 4px;">
  <span style="display:inline-block; width:80px; height:8px; border-radius:4px;
               background:var(--color-background-secondary); overflow:hidden;">
    <span style="display:block; width:[N]%; height:100%; border-radius:4px;
                 background:var(--color-background-info);"></span>
  </span>
  <span style="font-size:11px; color:var(--color-text-secondary);">[N]/100</span>
</span>
```

Replace `[N]` with the numeric score (0–100). For scores ≥75 use `info`, 50–74 use `warning`, <50 use `secondary`.

---

### C3. Proportion Bar (share / split)

Use when: showing market share split, pipeline composition %, or modality distribution inline.

```html
<span style="display:inline-flex; align-items:center; gap:6px; vertical-align:middle; margin:0 4px; font-size:11px;">
  <span style="display:inline-flex; width:120px; height:10px; border-radius:5px; overflow:hidden;">
    <span style="width:[A]%; background:var(--color-background-info);"></span>
    <span style="width:[B]%; background:var(--color-background-warning);"></span>
    <span style="width:[C]%; background:var(--color-background-secondary);"></span>
  </span>
  <span style="color:var(--color-text-secondary);">[Label A] [A]% · [Label B] [B]%</span>
</span>
```

---

### C4. Region Badge Row

Use when: summarizing reimbursement or approval status across regions in a sentence.

```html
<span style="display:inline-flex; gap:4px; flex-wrap:wrap; vertical-align:middle; margin:0 4px;">
  <span style="font-size:10px; padding:1px 6px; border-radius:3px;
               background:var(--color-background-success); color:var(--color-text-success);">US ✓</span>
  <span style="font-size:10px; padding:1px 6px; border-radius:3px;
               background:var(--color-background-success); color:var(--color-text-success);">EU ✓</span>
  <span style="font-size:10px; padding:1px 6px; border-radius:3px;
               background:var(--color-background-warning); color:var(--color-text-warning);">CN 谈判中</span>
  <span style="font-size:10px; padding:1px 6px; border-radius:3px;
               background:var(--color-background-secondary); color:var(--color-text-secondary);">JP —</span>
</span>
```

---

### C5. Delta Indicator

Use when: highlighting a change (LDL-C reduction %, ORR improvement, revenue growth) inline.

```html
<span style="display:inline-flex; align-items:center; gap:3px; font-size:12px;
             font-weight:500; vertical-align:middle; margin:0 3px;
             color:var(--color-text-success);">
  ↓ [N]%
</span>
```

Use `color-text-success` for favorable change (reduction in bad metric, increase in good metric), `color-text-warning` for unfavorable.

---

## Badge Reference

| Class | Color | Use for |
|---|---|---|
| `badge-approved` | Green | Approved / marketed |
| `badge-phase3` | Blue | Phase 3 / NDA / BLA |
| `badge-phase2` | Orange | Phase 2 |
| `badge-early` | Grey | Phase 1 / Preclinical |

## Modality Color Coding

| Modality | Background var | Text var |
|---|---|---|
| mAb / bispecific | `var(--color-background-info)` | `var(--color-text-info)` |
| siRNA / ASO | `var(--color-background-success)` | `var(--color-text-success)` |
| Small molecule / oral | `var(--color-background-warning)` | `var(--color-text-warning)` |
| Gene editing / cell therapy | `var(--color-background-secondary)` | `var(--color-text-secondary)` |
| Fusion protein / scaffold | `var(--color-background-primary)` + border | `var(--color-text-primary)` |
