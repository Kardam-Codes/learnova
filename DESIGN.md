# Design System Document: The Radical Educator

## 1. Overview & Creative North Star
### Creative North Star: "Structured Rebellion"
This design system moves beyond the polite, rounded aesthetics of modern SaaS. It embraces **Structured Rebellion**—a visual philosophy that combines the raw, unfiltered energy of Neobrutalism with the high-stakes precision required for an eLearning powerhouse. 

We break the "template" look by rejecting traditional elevation. There are no soft blurs here. We use intentional asymmetry, heavy-handed linework, and an aggressive typography scale to command attention. The UI is not a background; it is an active participant in the learning process. It feels less like a corporate portal and more like a high-end, underground editorial zine.

---

## 2. Colors & Surface Logic
The palette is built on high-voltage vibrance anchored by a deep, architectural black.

### The Palette
- **Primary (Yellow):** `#FACC15` (Used for "Main Action" energy)
- **Secondary (Pink):** `#F472B6` (Used for "Success" and "Progress" beats)
- **Tertiary (Cyan):** `#22D3EE` (Used for "Discovery" and "Interaction" cues)
- **Neutral/Base:** `surface: #f6f6f6` | `on_surface: #2d2f2f`

### The "Anti-Depth" Rule
Traditional elevation is prohibited. We do not use shadows to simulate light; we use them to simulate **physicality**. 
- **No-Blur Policy:** All shadows must be 100% opaque "hard drops." 
- **The Heavy Outline:** Sectioning is never done with 1px lines. We use a strictly enforced `4px` to `6px` solid black border (`on_surface`) to define boundaries. 

### Surface Hierarchy
Instead of gradients, use the **Surface Tiers** to define importance:
- **Surface-Container-Lowest (#ffffff):** The "Paper." Use this for the most critical interactive content.
- **Surface-Container-Highest (#dbdddd):** The "Sub-floor." Use this for background regions that hold multiple cards.

---

## 3. Typography
We use typography as a structural element. It is oversized, loud, and unapologetic.

*   **Display (Manrope - Bold/Extra Bold):** `3.5rem` to `2.25rem`. Use these for hero statements and module titles. They should feel almost uncomfortably large.
*   **Headlines (Manrope - Bold):** `2rem` to `1.5rem`. Used for section headers. Always paired with a `6px` bottom border or a high-contrast background block.
*   **Body (Inter - Medium):** `1rem` to `0.875rem`. Inter provides the "utility" needed for long-form educational content, ensuring readability isn't sacrificed for style.
*   **Labels (Inter - Bold):** `0.75rem`. Always uppercase. These act as "Sticker" text for metadata.

---

## 4. Elevation & Depth: The Hard Drop
In this system, "depth" is a graphic statement.

*   **The Signature Shadow:** Use a hard-offset shadow (e.g., `8px 8px 0px 0px #000000`). This is applied to cards, buttons, and input fields upon hover or focus.
*   **Tonal Layering:** To separate content without borders, use high-contrast color blocks. A `secondary_container` (#ffc0db) block sitting directly against a `surface` background creates a hard, digital edge that defines a zone without needing a single line.
*   **The Sticker Effect:** Badges and chips should not feel "embedded." They should look like physical stickers slapped onto the UI. Give them a `2px` black border and a slight rotation (1-2 degrees) for hero sections to break the grid's rigidity.

---

## 5. Components

### High-Visibility Buttons
- **Primary:** `primary` background, `4px` black border, `4px` hard black drop shadow. Text is `on_primary_fixed` (Bold).
- **State Change:** On hover, the shadow disappears, and the button "pushes" down (Translate Y: 4px), simulating a physical click.
- **Rounding:** `0px` (Strictly sharp corners).

### "Sticker" Badges & Chips
- **Style:** High-contrast backgrounds (`tertiary_container` or `secondary_container`).
- **Typography:** `label-md` uppercase.
- **Rule:** No shadows. Just a `2px` solid border.

### Editorial Cards
- **Construction:** `surface-container-lowest` fill, `4px` border. 
- **Padding:** Use the `spacing-6` (2rem) scale to give content massive breathing room inside the tight borders.
- **No Dividers:** Never use a line to separate card content. Use a background color shift (e.g., a `primary` header block inside a white card) to denote sections.

### Input Fields
- **Default:** `surface-container-lowest` background, `4px` border. 
- **Focus:** Background shifts to `primary_container` (#fed01b) with an `8px` hard drop shadow.
- **Error:** Background shifts to `error_container` (#f95630).

### Progress Indicators
- **Visual:** Use a "Chunk" system. Instead of a smooth loading bar, use a series of high-contrast blocks that fill up, separated by `2px` gaps.

---

## 6. Do's and Don'ts

### Do
- **DO** use massive white space. High-contrast systems need room to breathe, or they become illegible.
- **DO** overlap elements. Let a "Sticker" badge bleed over the edge of a card's border.
- **DO** use the `spacing-20` (7rem) scale for section breaks to create an editorial, magazine-like flow.

### Don't
- **DON'T** use subtle greys. If it’s not black or a vibrant brand color, it probably doesn't belong.
- **DON'T** use border-radius. This system is built on the strength of the right angle.
- **DON'T** use 1px lines. They look accidental. If you draw a line, make it `4px` minimum.
- **DON'T** use soft transitions. Hover states should be instant and tactile.