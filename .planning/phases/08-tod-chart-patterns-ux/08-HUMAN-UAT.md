---
status: partial
phase: 08-tod-chart-patterns-ux
source: [08-VERIFICATION.md]
started: "2026-06-12T00:00:00Z"
updated: "2026-06-12T00:00:00Z"
---

## Current Test

[awaiting human testing]

## Tests

### 1. Time-of-Day Chart renders on upload
expected: Upload real CGM file → chart shows colored line data (not blank canvas). The `const patterns` injection and `typeof patterns !== 'undefined'` guard are wired correctly; browser rendering confirms the fix works end-to-end.
result: [pending]

### 2. Out-of-range card suppression
expected: With a file where no 60-min hourly patterns fall outside 70–180 mg/dL, the "Time Windows to Focus On" card does not appear (no empty wrapper rendered).
result: [pending]

### 3. WD/WE split + % out of range end-to-end
expected: With 14+ days of data, behavioral patterns rows show "WD 145 · WE 162" notation, and insight cards show "avg X mg/dL · Y% out of range" text in both Above Range and Below Range sections.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
