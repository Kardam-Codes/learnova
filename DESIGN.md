# DESIGN.md

## Current Design Direction
Learnova currently uses a bold, outlined UI system with strong page structure.

It is not minimal SaaS styling.

The current direction combines:
- strong borders
- hard shadows
- editorial headings
- high-contrast cards
- visible interaction states

This style is already present across learner pages and should remain the base for instructor/admin pages too.

---

## Core Visual Principles

### 1. Strong Structure
- Use visible borders to define regions
- Prefer bold containment over subtle separators
- Page sections should feel intentionally boxed and grouped

### 2. Consistent Density
- Cards should not feel randomly cramped or randomly spacious
- Similar UI patterns should share padding and spacing rhythm
- Typography size should stay readable across dashboard, detail, and player contexts

### 3. Editorial Hierarchy
- Page titles should be strong
- Section titles should clearly anchor a region
- Metadata should be smaller and calmer
- Body copy should stay readable, never tiny

### 4. Practical Interaction Design
- Active states must be obvious
- Hover states should feel responsive
- Search, tabs, buttons, and cards should look like part of one system

---

## Theme

The app supports:
- light mode
- dark mode

Theme is handled through CSS variables in `src/styles/app.css`.

Do not create page-specific unrelated theme systems.

---

## Color System

Current core colors:
- background / surface
- panel / panel-alt
- ink / line
- yellow
- pink
- cyan
- muted text

Usage principles:
- use yellow, pink, and cyan as accent colors
- do not let all accents compete equally on one screen
- status colors should be meaningful, not decorative noise

---

## Typography

Current typography roles:
- Brand wordmark: serif / italic feel
- Main headings: Manrope-like bold sans
- Body copy: Inter / system sans
- Labels and chips: uppercase, compact, bold

Consistency rules:
- do not shrink body text too much
- do not mix unrelated font families
- keep dashboard cards, content rows, and sidebar labels visually aligned

---

## Card Language

Cards should generally use:
- solid panel background
- thick border
- bold title
- readable internal spacing
- hard shadow when appropriate

Use cards for:
- course cards
- profile blocks
- progress panels
- reviews
- instructor metric cards
- grouped forms

---

## Buttons and Controls

Current control language:
- thick border
- bold text
- compact but readable padding
- hard-shadow interaction

Use SVG icons only.

Do not use:
- emoji icons
- text inside icons
- weak, low-contrast controls

---

## Existing Page Patterns

### My Courses
- navbar
- page header
- search
- split layout
- course grid
- profile panel

### Course Detail
- navbar
- hero header
- tabs + toolbar
- searchable content list

### Reviews
- shared course hero
- tabs
- rating summary
- review entry
- review feed

### Lesson Player
- immersive shell
- sidebar + main content
- active content emphasis
- bottom progression CTA

---

## PDF Viewing

Documents now use:
- PDF.js
- lazy loading
- fullscreen support
- keyboard shortcuts

This is the preferred document-viewing direction, not third-party embed viewers.

---

## What New Pages Must Preserve

- same navbar language
- same card language
- same border/shadow language
- same spacing rhythm
- same typography hierarchy
- same theme variables
- same SVG icon approach

For detailed implementation rules, see:
- [PAGE_CONSISTENCY.md](./PAGE_CONSISTENCY.md)
