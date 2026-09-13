# Reference: Rich Animated Vector SVG Standards for GitHub

## 1. Why Standalone Vector SVG?
While Mermaid is excellent for quick flowcharts, custom vector SVGs provide:
- Custom typography, exact pixel dimensions, and custom glassmorphism styling.
- Linear/radial gradients with glowing drop-shadow filters (`feDropShadow`).
- Pure CSS animations (`stroke-dasharray` animated connection lines) that execute natively inside GitHub READMEs!
- Resolution independence: 100% crisp on 4K, 5K, and Retina displays.

---

## 2. GitHub SVG Security & Rendering Invariants
1. **No External Fonts**: Always use system font stacks (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto...`) because GitHub's image proxy blocks external web fonts (`@import url(...)`).
2. **Inline CSS Styles**: Keep `<style>` tags enclosed within `<defs>`.
3. **No Embedded JavaScript**: GitHub's `camo` sanitizer strips `<script>` tags from SVGs. Use CSS `@keyframes` animations instead.
4. **ViewBox Scaling**: Always provide `viewBox="0 0 W H"` and `width="100%"` for fluid responsive scaling.

---

## 3. Recommended Dark Slate Palette
- Background: `#090D16` to `#0F172A`
- Cards: `#1E293B` border `#334155`
- Primary (Indigo): `#6366F1`
- Success (Emerald): `#10B981`
- Accent (Purple): `#A855F7`
- Warning (Amber): `#F59E0B`
- Text (Primary): `#F8FAFC`, Secondary: `#94A3B8`
