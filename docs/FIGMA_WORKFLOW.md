# Figma-to-Code Workflow

> How to use the Figma MCP server to synchronize designs with the 42-training codebase.

---

## Table of contents

1. [Overview](#overview)
2. [Canonical references](#canonical-references)
3. [Prerequisites](#prerequisites)
4. [Design token mapping](#design-token-mapping)
5. [Reading designs from Figma](#reading-designs-from-figma)
6. [Implementing a design](#implementing-a-design)
7. [Code Connect](#code-connect)
8. [Writing back to Figma](#writing-back-to-figma)
9. [Component inventory](#component-inventory)
10. [Conventions](#conventions)

---

## Overview

The project uses the **Figma MCP server** (`claude.ai Figma`) to bridge design and code. The MCP server provides tools to:

- **Read** designs from Figma (`get_design_context`, `get_screenshot`, `get_metadata`)
- **Search** the design system (`search_design_system`)
- **Map** Figma components to code components (`Code Connect`)
- **Write** designs back into Figma (`use_figma`)
- **Generate** diagrams in FigJam (`generate_diagram`)

The frontend stack is **Next.js 16 + React 19 + TypeScript**.

Current implementation state:
- the shipped code still relies heavily on `apps/web/app/globals.css`
- the legacy workflow in this document originally assumed plain global CSS as the styling system

Approved product direction:
- the **Figma design file is the canonical UI and UX reference**
- the authenticated app shell is defined in Figma before page implementation
- frontend governance is moving toward **Tailwind + centralized tokens + themes/skins + accessibility controls**
- implementation work must distinguish between the current code state and the target governance state

## Canonical references

Use these references in this order:

### 1. Product and flow framing

- FigJam board:
  `https://www.figma.com/board/GEBta7NTiYf3I8e4rZluHI/Sans-titre?node-id=0-1&p=f&t=Anj427ymgsVB9ZE5-0`

This board is the reference for:
- product flow inventory
- cross-flow coherence
- error and exception branches
- prioritization and design discussion

### 2. Canonical UI design

- Design file:
  `https://www.figma.com/design/qqaNVWa3c7UoVrrBo9gk3c/42-Training-%E2%80%94-Hacker-HUD-Interface?node-id=0-1&p=f&t=8sdMMNFQH1ov2ppT-0`

This file is the reference for implementation.

Validated pages currently include:
- `00 — App Shell (Canonical)`
- `01 — Login`
- `02 — Dashboard`
- `03 — Track Explorer`
- `04 — Module Learning`
- `05 — Defense Session`
- `06 — AI Mentor`

### 3. Canonical authenticated shell rules

The authenticated shell must follow the validated Figma behavior:

- the sidebar never disappears
- desktop expanded: `240px` sidebar
- desktop collapsed: `48px` rail
- tablet collapsed: `48px` rail with overlay expansion
- mobile collapsed: `40px` rail with overlay expansion
- persistent rail actions remain available on all breakpoints

Minimum persistent rail slots:
- collapse / expand control
- primary action slot
- secondary action slot when relevant
- terminal or live-status slot

---

## Prerequisites

1. **Figma MCP server** connected in Claude Code (the `claude.ai Figma` server must be active)
2. **Figma file** for 42-training (create one or use an existing file)
3. Access to the codebase at `apps/web/`

### Verifying the MCP connection

Use `whoami` to confirm the Figma MCP server is connected and identify the authenticated account.

---

## Design token mapping

The codebase defines design tokens as CSS custom properties in `apps/web/app/globals.css`. When working in Figma, map these tokens to Figma variables.

### Color palette

| CSS variable | Hex | Usage | Figma variable name |
|-------------|-----|-------|-------------------|
| `--bg` | `#f7f0e5` | Page background (warm cream) | `color/bg` |
| `--panel` | `rgba(255, 252, 247, 0.86)` | Panel/card background (frosted glass) | `color/panel` |
| `--ink` | `#1c1a17` | Primary text | `color/ink` |
| `--muted` | `#645f58` | Secondary text | `color/muted` |
| `--line` | `rgba(28, 26, 23, 0.12)` | Borders and dividers | `color/line` |
| `--shell` | `#1c5d63` | Shell track accent (teal) | `color/shell` |
| `--c` | `#b24c2b` | C track accent (rust) | `color/c` |
| `--python` | `#355f3b` | Python track accent (sage green) | `color/python` |
| `--accent` | `#d8a657` | Gold accent, highlights | `color/accent` |

### Typography

| Role | Font | Weight | Size |
|------|------|--------|------|
| Body | IBM Plex Sans | 400 | 15px, line-height 1.55 |
| Headings | Space Grotesk | 700 | clamp(1.8rem, 4vw, 2.8rem) for h1 |
| Code/terminal | IBM Plex Mono | 400 | 13px |
| Eyebrow labels | IBM Plex Sans | 600 | 11-12px, uppercase, tracking 0.06em |

### Spacing scale

The codebase uses a consistent gap scale: `4px`, `6px`, `8px`, `10px`, `12px`, `14px`, `16px`, `18px`, `20px`.

### Border radius

| Element | Radius |
|---------|--------|
| Large panels | 18px |
| Cards | 14px |
| Small elements | 8px |
| Pills and badges | 999px (fully rounded) |

---

## Reading designs from Figma

### Step 1: Extract file key and node ID from the URL

Figma URLs follow this pattern:

```
figma.com/design/:fileKey/:fileName?node-id=:nodeId
```

Convert dashes to colons in `nodeId` (e.g., `12-34` becomes `12:34`).

For branch URLs:
```
figma.com/design/:fileKey/branch/:branchKey/:fileName
```
Use `branchKey` as the file key.

### Step 2: Get the design context

Call `get_design_context` with the `fileKey` and `nodeId`. This returns:

- **Code** — React + Tailwind reference code (adapt to our CSS-in-globals stack)
- **Screenshot** — Visual reference of the selected node
- **Contextual hints** — Component documentation, design annotations, token mappings

### Step 3: Get a screenshot (optional)

Use `get_screenshot` for a visual reference when `get_design_context` alone is insufficient. Useful for verifying layout, spacing, and visual hierarchy.

### Step 4: Get metadata

Use `get_metadata` for file-level information (pages, components, styles).

---

## Implementing a design

The output from `get_design_context` is a **reference**, not final code. Always adapt it to match the project conventions.

### Adaptation checklist

1. **Replace Tailwind classes** with existing CSS classes from `globals.css` or new BEM-style classes
2. **Use CSS custom properties** (`var(--accent)`) instead of raw hex values
3. **Match the component pattern** — server components for data fetching, client components (`"use client"`) for interactivity
4. **Reuse existing components** before creating new ones:
   - `SourcePolicyBadge` for trust tier indicators
   - `TerminalPane` for terminal output display
   - `TmuxSessions` for session lists
   - `Pill` (inline in pages) for badges
5. **Follow the layout structure**:
   - `<main className="page-shell">` for page wrapper
   - `.panel` for card containers
   - `.section` / `.section-heading` for content areas
   - `.breadcrumb` for navigation context
6. **Check for design annotations** — notes from the designer override default assumptions
7. **Check for Code Connect mappings** — if a Figma component has a Code Connect mapping, use the mapped codebase component directly

### Example workflow

```
1. Get Figma URL from the designer
2. Parse fileKey and nodeId
3. Call get_design_context → get reference code + screenshot
4. Identify reusable components (panel, pill, action-btn, etc.)
5. Create or edit the page in apps/web/app/<feature>/page.tsx
6. Map Figma tokens → CSS custom properties
7. Add new CSS classes to globals.css if needed (BEM naming)
8. Verify with tsc --noEmit and visual check
```

---

## Code Connect

Code Connect links Figma components to their code equivalents. This allows `get_design_context` to return the actual codebase component instead of generic code.

### Setting up mappings

Use `get_code_connect_suggestions` to see which Figma components can be mapped, then `send_code_connect_mappings` to create the links.

### Current component inventory for mapping

| Figma component | Code target | File |
|----------------|------------|------|
| Source badge | `<SourcePolicyBadge tier={tier} />` | `app/components/SourcePolicyBadge.tsx` |
| Terminal pane | `<TerminalPane session={name} />` | `app/components/TerminalPane.tsx` |
| Navigation header | `<NavHeader />` | `app/components/NavHeader.tsx` |
| Auth status | `<AuthStatus />` | `app/components/AuthStatus.tsx` |
| Boot sequence | `<BootSequence lines={lines} />` | `app/components/BootSequence.tsx` |
| Tmux sessions | `<TmuxSessions sessions={sessions} />` | `app/components/TmuxSessions.tsx` |
| Tabbed terminal | `<TabbedTerminalViewer sessions={sessions} />` | `app/components/TabbedTerminalViewer.tsx` |

### Viewing existing mappings

Call `get_code_connect_map` to see all current mappings. Call `add_code_connect_map` to register new ones.

---

## Writing back to Figma

Use `use_figma` to create or update designs in Figma from code. This is useful for:

- Keeping Figma in sync after code-side changes
- Generating screens from new pages
- Building a component library from existing code

### Important

Always load the `figma-use` skill **before** calling `use_figma`. This skill provides the Plugin API context needed to avoid common failures.

### Workflow for syncing code changes back

```
1. Identify the code change (new component, updated layout)
2. Load the figma-use skill
3. Use search_design_system to find matching tokens and components
4. Call use_figma to create or update the Figma nodes
5. Verify the result with get_screenshot
```

---

## Component inventory

### CSS class reference for Figma mapping

| Visual pattern | CSS class(es) | Notes |
|---------------|--------------|-------|
| Page wrapper | `.page-shell` | max-width: 1280px, centered grid |
| Card / panel | `.panel` | Backdrop blur, rounded corners, shadow |
| Hero section | `.hero`, `.hero-copy` | Top-of-page feature area |
| Section | `.section`, `.section-heading` | Content blocks with eyebrow + h2 |
| Metric card | `.metric-card` | Key-value display (label + strong) |
| Track card | `.track-card`, `.track-card.active` | Track selector with colored border |
| Pill / badge | `.pill`, `.pill--done`, `.pill--in_progress`, `.pill--todo` | Status tags |
| Action button | `.action-btn`, `.action-btn:disabled` | Primary CTA |
| Source badge | `.spb`, `.spb--high`, `.spb--medium`, `.spb--low`, `.spb--blocked` | Trust indicators |
| Breadcrumb | `.breadcrumb`, `.breadcrumb-sep` | Page navigation |
| Terminal | `.terminal-pane`, `.terminal-pane-content` | Dark console output |
| Error display | `.defense-error` | Red-tinted error messages |
| Form field | `.defense-field`, `.defense-textarea` | Input containers |
| Eyebrow label | `.eyebrow` | Uppercase small label |
| Muted text | `.muted` | Secondary color text |
| Feedback block | `.defense-feedback--good/--partial/--low` | Color-coded left border |

### Responsive breakpoints

| Breakpoint | Target |
|-----------|--------|
| Default | Mobile-first, single column |
| `min-width: 900px` | Desktop two-column layouts |
| `max-width: 640px` | Compact mobile overrides |

---

## Conventions

### Do

- Map Figma color styles to CSS custom properties, not raw hex
- Use the existing spacing scale (4-6-8-10-12-14-16-18-20px)
- Follow BEM-like naming for new CSS classes (`.feature-element--modifier`)
- Add new styles to the end of `globals.css` under a section comment
- Verify TypeScript compiles after implementing (`npx tsc --noEmit`)
- Prefer server components; use `"use client"` only when state or interactivity is needed

### Do not

- Do not introduce Tailwind, CSS modules, or styled-components
- Do not duplicate existing CSS patterns — check `globals.css` first
- Do not inline styles unless the value is dynamic (e.g., computed dimensions)
- Do not add UI polish disconnected from pedagogical value (per CLAUDE.md)
- Do not bypass the architecture boundaries (`apps/web` is presentation only)
