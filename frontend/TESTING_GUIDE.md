# Revenue OS: Comprehensive Testing Guide

This guide is designed for the QA team or clients to verify every UI polish, animation, and route integration applied across the Revenue OS public site.

## 1. Global Navigation & Architecture
**Objective:** Verify that the global Header component works consistently across all public pages.
- [ ] Go to `http://localhost:3000/`.
- [ ] Verify the **Header** appears at the top. 
- [ ] Hover over the `Features`, `Pricing`, `Demo`, and `Contact` links. Verify the text brightens and a small dot indicator appears beneath the active page.
- [ ] Hover over the `Revenue OS` logo. Verify a subtle glow shadow expands behind the icon.
- [ ] Click the `Dashboard` button. Verify it scales up slightly on hover and clicks through to the login/dashboard interface.
- [ ] Navigate to `/features`, `/pricing`, `/demo`, and `/contact`. Ensure the header persists seamlessly without reloading or jumping.

## 2. Home Page (`/`)
**Objective:** Verify trust elements, layout padding, and entry animations.
- [ ] Hard refresh the Home page.
- [ ] Verify the hero text and "Start free trial" buttons slide up smoothly from the bottom (fade-in slide-in).
- [ ] Verify the `Revenue OS 2.0 is now live` pill pulses smoothly and slightly enlarges on hover.
- [ ] Scroll down to the **Trusted By** banner.
- [ ] Hover your mouse over the grayscale brand names (e.g., `Acme Corp`). Verify they smoothly transition to full brightness.

## 3. Pricing Page (`/pricing`)
**Objective:** Verify the interactive toggle and responsive card layouts.
- [ ] Navigate to `/pricing`.
- [ ] Click the **Monthly** and **Annually** toggle buttons.
- [ ] Verify the dark pill slides smoothly behind the selected option.
- [ ] Verify the pricing values dynamically swap (e.g., `$299` to `$349`) utilizing a vertical slide transition.
- [ ] Hover over the three pricing cards. Verify they smoothly scale up and the border glows to indicate focus.

## 4. Features Page (`/features`)
**Objective:** Verify grid alignments and interactive hover states.
- [ ] Navigate to `/features`.
- [ ] Hover over the `Predictive Lead Scoring` card. Verify the large background robot icon enlarges.
- [ ] Hover over the `Native WhatsApp` and `Universal Ingestion` cards. Verify the center icons rotate subtly.
- [ ] Hover over the `Deep ROI Analytics` card. Verify the background bar chart columns scale up sequentially from left to right.

## 5. Contact & Demo Pages (`/contact`, `/demo`)
**Objective:** Verify the newly rebuilt, enterprise-grade layouts.
- [ ] Navigate to `/contact`.
- [ ] Verify the split layout: Information on the left, Form on the right.
- [ ] Hover over the Email, Phone, and Address blocks. Verify the border and icon colors transition smoothly to emerald.
- [ ] Focus on the input fields. Verify an emerald ring appears.
- [ ] Navigate to `/demo`.
- [ ] Verify the video player mockup. Hover over it to see the grayscale mock UI transition into color, and the central play button scale up.
- [ ] Verify the interactive calendar grid layout is properly aligned and responsive.

## 6. Mobile Responsiveness Check
- [ ] Open browser Developer Tools (F12) and switch to Mobile Device Mode (e.g., iPhone 14 Pro).
- [ ] Ensure the Global Header collapses its standard links and the "Dashboard" button is either hidden or resized properly according to the Tailwind breakpoints.
- [ ] Ensure all multi-column grids (like the Pricing cards, Features grid, and Contact split-layout) stack cleanly into single columns without horizontal scrolling.
