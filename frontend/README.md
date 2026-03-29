# Pixie Scorecard Frontend

React single-page application that renders the `pixie test` HTML scorecard report.
Built with Vite and compiled to a single self-contained HTML file that ships
inside the Python package.

## Quick Start

```bash
# Install dependencies
npm install

# Start dev server with mock data
npm run dev

# Build for production (outputs to ../pixie/assets/index.html)
npm run build
```

## Stack

- **React 19** + **TypeScript 5.7**
- **Vite 6** bundler
- **vite-plugin-singlefile** — inlines all JS/CSS into one HTML file

## Project Structure

```text
src/
├── main.tsx              # Entry point (dev: loads mock-data.json, prod: reads window global)
├── App.tsx               # Root component with modal state management
├── types.ts              # TypeScript interfaces matching Python data models
├── styles.css            # "Ink & Signal" design theme (CSS variables)
└── components/
    ├── BrandHeader.tsx   # Sticky header with logo, feedback button, GitHub CTA
    ├── Overview.tsx      # Test run overview: command, timestamp, pass/fail summary
    ├── StatusBadge.tsx   # PASS / FAIL / ERROR badge
    ├── TestSection.tsx   # Per-test card with error messages and assert cards
    ├── AssertCard.tsx    # Single assert result: scoring strategy, criteria, tabbed passes
    ├── PassTable.tsx     # Evaluator summary table + per-input detail table with scores
    ├── EvalDetailModal.tsx  # Modal: score, reasoning, input/output, metadata
    └── FeedbackModal.tsx    # Modal: user feedback form
```

## How It Works

### Production (inside `pixie test`)

1. Python's `generate_scorecard_html()` loads the compiled `index.html` template
2. Replaces `"__PIXIE_DATA_PLACEHOLDER__"` with JSON.dumps(report_data)
3. The saved HTML file opens standalone (`file://`) — no server needed, no external deps

### Development

```bash
npm run dev
```

Vite serves the app at `http://localhost:5173`. In dev mode, `main.tsx` fetches
`/mock-data.json` instead of reading `window.PIXIE_REPORT_DATA`, so you can
iterate on the UI without running `pixie test`.

Edit `public/mock-data.json` to test different data shapes. The mock data mirrors
the realistic e2e fixture (4 tests, 5 dataset items, 4 evaluators).

### Build

```bash
npm run build
```

Produces `../pixie/assets/index.html` — a single HTML file (~214 KB, ~66 KB gzip)
with all React code, CSS, and assets inlined. This file is gitignored because it's
a build artifact; it must be rebuilt after any frontend changes.

## Data Interface

The React app expects a `ScorecardReportData` object (see `src/types.ts`):

```typescript
interface ScorecardReportData {
  command_args: string;
  timestamp: string;
  summary: string; // e.g. "2/4 tests passed"
  pixie_repo_url: string;
  feedback_url: string;
  brand_icon_url: string;
  test_records: TestRecordData[];
}
```

Each `TestRecordData` contains `name`, `status`, optional `message`, and an array
of `AssertRecordData` with the full evaluation tensor (`results[passes][inputs][evaluators]`).

## Design Theme: "Ink & Signal"

- Warm stone background (`#faf9f7`) with cream surface cards
- Monospace headings (JetBrains Mono / Fira Code / Menlo)
- Serif body text (Charter / Georgia / Times)
- Emerald pass (`#059669`), coral fail (`#dc2626`), purple accent (`#7c3aed`)
- Responsive layout, sticky header, modal overlays
