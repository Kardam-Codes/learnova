# PAGE_CONSISTENCY.md

## File Metadata Convention
Every new frontend file should begin with a short header comment like:

```js
/*
 * File: ExamplePage.jsx
 * Owner: KARDAM | YUG | BOTH CAN ADD
 * Purpose: One-line reason this file exists.
 * What it is: Short description of what this file renders or controls.
 */
```

This is required because the current repo workflow depends on readable ownership and intent.

---

## What Yug's Codex Must Follow
This document is for the **frontend page system**, especially when adding **Instructor/Admin-side pages**.

The goal is:
- preserve the existing app theme
- preserve the current frontend folder structure
- preserve the current visual language
- avoid introducing a second UI system
- avoid mixing backend-style module scaffolding into the React frontend

---

## Current Frontend Architecture
The current frontend is **not** feature-module based.

For the frontend, the architecture currently used is:
- `pages/` for route-level screens
- `components/` for reusable UI blocks
- `context/` for shared app state
- `data/` for mock/demo data
- `utils/` for helpers and route builders
- `styles/` for the global visual system

So the current frontend architecture is best described as:

**Page/Component-Based Layered React Architecture**

Do not create new frontend folders like:
- `src/modules/admin/...`
- `src/modules/instructor/...`
- `src/features/...`

unless the whole frontend is intentionally refactored later.

For now, all new instructor/admin UI should follow the same structure already used by learner pages.

---

## Current Frontend Folder Structure
Use this structure:

```plaintext
src/
├── components/
├── context/
├── data/
├── pages/
├── styles/
├── utils/
├── App.jsx
└── main.jsx
```

### Page Placement Rules
- Route-level screens go in `src/pages/`
- Reusable UI blocks go in `src/components/`
- Shared mock/demo data goes in `src/data/`
- Shared route helpers / formatting helpers go in `src/utils/`
- Visual rules go in `src/styles/app.css`

### Do Not
- do not create placeholder frontend module folders
- do not create empty scaffold files
- do not duplicate the learner page structure under a second top-level UI system
- do not add isolated CSS files unless there is a very strong reason

---

## Visual System Rules
Instructor pages must visually belong to the same product as learner pages.

### Theme Rules
- Support the existing light/dark theme system
- Use the existing CSS variables from `:root` and `:root[data-theme="dark"]`
- Do not hardcode unrelated color systems for instructor pages
- New colors should be introduced only if they fit the existing palette

### Existing Core Tokens
Current design language is built around:
- `--bg`
- `--panel`
- `--panel-alt`
- `--ink`
- `--line`
- `--yellow`
- `--pink`
- `--cyan`
- `--muted`
- `--hard-shadow`
- `--card-shadow`

New instructor pages should reuse these first.

### Border + Shadow Language
The current UI style uses:
- thick outlined borders
- bold card edges
- hard offset shadows

So new pages should continue using:
- `border: 4px solid var(--line)`
- `box-shadow: var(--hard-shadow)` or `var(--card-shadow)`

Do not suddenly switch instructor pages to:
- soft glassmorphism
- subtle gray-only enterprise UI
- borderless cards
- rounded SaaS gradients unrelated to the rest of the app

---

## Typography Consistency Rules
Typography should feel consistent across learner and instructor pages.

### Current Type Roles
- Brand wordmark: serif / italic style
- Major headings: `Manrope, "Segoe UI", sans-serif`
- Body copy: `Inter, "Segoe UI", sans-serif`
- Labels / chips / badges: uppercase, compact, bold

### Use These Patterns
- Page title: bold, large, Manrope
- Section title: bold, medium-large, Manrope
- Card title: bold, medium, Manrope
- Body text: readable, not tiny
- Metadata text: smaller, muted, but still readable

### Avoid
- very small body text
- multiple unrelated font families
- decorative fonts for normal UI
- large shifts in text size between similar cards or rows

---

## Spacing and Layout Rules
Spacing across new pages should feel like the learner pages.

### Top-Level Page Pattern
For normal non-player pages:

```plaintext
Page
├── Navbar
├── Page Card / Main Shell
│   ├── Hero / Header
│   ├── Toolbar
│   └── Main Content
```

### Shared Spacing Principles
- Navbar has generous horizontal breathing space
- Page card padding is medium, not cramped
- Cards inside a page should share the same rhythm
- Related sections should have tight grouping
- Separate sections should have visibly distinct spacing

### Avoid
- one page being very compressed while the next is overly spacious
- inconsistent gaps between cards of the same type
- oversized empty zones that make content feel disconnected

---

## Navbar Rules
All instructor/admin pages should reuse the same navbar language.

### Keep
- left brand area
- right utility controls
- same border thickness
- same theme toggle style
- same user/avatar treatment pattern

### Do Not
- create a different navbar style for admin pages
- move to a tiny top strip
- introduce a second logo system
- make the admin navbar look like a different app

If role-based nav items are needed, add them inside the existing navbar pattern rather than replacing the navbar.

---

## Card Design Rules
The app is heavily card-based.

### Existing Card Language
Cards generally use:
- solid panel background
- thick border
- bold headings
- controlled spacing
- hard shadow or flat bordered grouping

### For New Instructor Cards
Use cards for:
- dashboard metrics
- list containers
- forms
- side panels
- modal content

### Avoid
- cards with wildly different padding from the rest of the app
- tiny dense enterprise rows inside huge bold cards
- mixing soft rounded SaaS cards with the existing outlined blocks

---

## Forms and Input Rules
Instructor pages will likely add many forms. They must still fit the existing UI.

### Existing Input Style
Use:
- visible borders
- bold labels
- enough padding for comfortable interaction
- same dark/light theme adaptation

### Recommended Pattern
- label above field
- medium vertical gap
- consistent button sizing
- clear grouped field sections

### Avoid
- ultra-minimal underlined inputs
- browser-default styling mixed with custom buttons
- tiny label text

---

## Tables, Lists, and Kanban Rules
Instructor/Admin pages will likely include dashboards, tables, and kanban boards.

### Tables
Should visually match the app by using:
- bordered table container
- strong row separation
- clear status tags
- readable density, not tiny admin-console density

### Kanban
Should use:
- outlined columns
- strong section titles
- consistent card rhythm
- same chip/badge system as rest of app

### Avoid
- introducing a generic data-grid aesthetic that feels unrelated to the learner pages

---

## Tabs, Filters, and Toolbars
Existing learner pages already use route-like tabs and top toolbars.

New instructor pages should follow the same idea:
- tabs should use the same active/inactive styling pattern
- filters and search should align with tabs visually
- toolbar spacing should match current course/reviews pages

Do not introduce a completely different tab system.

---

## Sidebar Rules
If instructor pages need sidebars:
- use the same clear boundary treatment as the learning sidebar
- make active state obvious
- keep readable typography
- keep interaction states deliberate

Avoid:
- ghost sidebars with weak active state
- tiny text links packed too tightly

---

## Icon Rules
Very important:
- use SVG icons only
- do not use emojis
- do not place text inside icons

Match the current icon behavior:
- clean stroke-based icons
- compact utility size
- semantic button labels through adjacent text or `aria-label`

---

## Page Consistency Rules by Type

### 1. Dashboard Pages
Examples:
- course dashboard
- reporting dashboard
- instructor home

Must use:
- navbar
- page header
- grid or split layout
- metric cards with consistent hierarchy

### 2. Detail / Form Pages
Examples:
- course form
- quiz builder
- lesson editor

Must use:
- strong page title
- grouped sections/cards
- consistent spacing between form groups
- action toolbar that matches the rest of the app

### 3. Data / Management Pages
Examples:
- attendees list
- reporting table
- content list

Must use:
- visible section boundary
- readable rows
- consistent controls
- filters/search that align with top toolbar

---

## Shared Interaction Rules
Across new pages:
- hover states should be visible
- active states should be obvious
- clickable cards should feel clickable
- selected rows/items should be clearly highlighted
- transitions should be subtle and intentional

Do not add heavy animation for normal admin flows.

---

## Mock Data and Wiring Rules
Until backend integration is complete:
- keep mock/demo data in `src/data/`
- do not bury mock data inside pages
- keep route helpers in `src/utils/`
- keep view logic in pages/components, not in random helper files

---

## Current Learner Pages as Style Reference
Use these pages as the visual source of truth:
- `src/pages/MyCoursesPage.jsx`
- `src/pages/CourseDetailPage.jsx`
- `src/pages/CourseReviewsPage.jsx`
- `src/pages/LessonPlayerPage.jsx`

Use these reusable UI/style references too:
- `src/components/Navbar.jsx`
- `src/components/CourseHeader.jsx`
- `src/components/CourseCard.jsx`
- `src/components/ProfilePanel.jsx`
- `src/styles/app.css`

---

## How Instructor Pages Should Be Added
Example pattern:

```plaintext
src/pages/AdminCoursesDashboardPage.jsx
src/pages/CourseFormPage.jsx
src/pages/QuizBuilderPage.jsx
src/pages/ReportingDashboardPage.jsx
```

Supporting reusable parts:

```plaintext
src/components/AdminMetricCard.jsx
src/components/AdminTable.jsx
src/components/AdminToolbar.jsx
src/components/FormSectionCard.jsx
src/components/KanbanColumn.jsx
```

This keeps instructor pages aligned with the current frontend architecture instead of creating a second architecture.

---

## Non-Negotiable Rules for Yug's Codex
1. Do not break the current frontend folder structure.
2. Do not create unused scaffold folders or placeholder module trees.
3. Do not introduce a second design system.
4. Do not use emojis.
5. Use SVG icons only.
6. Keep metadata headers in files.
7. Keep typography readable and consistent.
8. Reuse current navbar, card, chip, button, and toolbar language.
9. Match the learner-side spacing rhythm.
10. If a new admin page needs a pattern, extend the current system instead of replacing it.

---

## Short Instruction Yug Can Paste to Codex
Use the current Learnova frontend as the source of truth.

Build new Instructor/Admin pages using the existing frontend architecture:
- pages in `src/pages`
- reusable blocks in `src/components`
- mock data in `src/data`
- helpers in `src/utils`
- styling in `src/styles/app.css`

Match the same:
- navbar language
- card/border/shadow language
- typography hierarchy
- spacing rhythm
- tabs/toolbars
- SVG icon style
- light/dark theme behavior

Do not introduce:
- feature-module frontend folders
- a second admin-only design system
- emoji icons
- empty scaffold files/folders

Always include file metadata headers with owner, purpose, and what-it-is.
