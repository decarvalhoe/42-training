# Frontend Styling Governance

## Goal

Provide one maintainable styling system that matches the validated Figma reference while remaining extensible for accessibility controls and future unlockable skins.

## Target stack

- Tailwind for layout, spacing, responsive behavior and component composition
- centralized design tokens through CSS custom properties
- a small global CSS layer for reset, token declarations and compatibility with legacy surfaces
- data attributes on the root element for theming and accessibility preferences

## Principles

1. Figma remains the canonical UI and UX reference.
2. Tailwind is used for new shell and component composition work.
3. Hardcoded one-off page CSS should be reduced over time, not expanded.
4. Existing global CSS can remain temporarily for legacy pages, but new layout work should not deepen the monolith.
5. Themes and accessibility modes must be implemented through shared tokens and root attributes, not per-page overrides.

## Root attributes

The frontend now reserves these root attributes:

- `data-theme`
- `data-contrast`
- `data-density`
- `data-motion`

These attributes are the contract for:
- base design theme selection
- future unlockable skins
- high-contrast mode
- compact vs comfortable density
- motion reduction policies

## Theme contract

Current baseline:
- `hacker-hud` is the canonical default aligned with Figma

Reserved future theme:
- `warm-classic`

Future skins must:
- reuse the same semantic tokens
- preserve component geometry and interaction behavior
- avoid duplicating component CSS for each skin

## Shell contract

The authenticated shell must preserve these rules:

- the sidebar never disappears
- desktop expanded: `240px`
- desktop collapsed rail: `48px`
- tablet collapsed rail: `48px` with overlay expansion
- mobile collapsed rail: `40px` with overlay expansion
- persistent rail actions remain available on all breakpoints

## Accessibility contract

The styling system must support:

- visible keyboard focus
- reduced motion
- contrast variants
- readable density modes
- future font-size and readability controls without page-specific hacks

## Migration rule

When migrating legacy pages:
- prefer Tailwind for new layout and shell work
- keep tokens centralized in global CSS
- remove page-specific global CSS only when the equivalent Tailwind composition is in place
- avoid mixing duplicate layout abstractions in both Tailwind and legacy CSS for the same surface
