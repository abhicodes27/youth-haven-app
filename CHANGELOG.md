# Changelog & Review Log

This project went through several rounds of external review. Rather than
scatter that history across commit messages, this file keeps a record of
what was flagged, what changed in response, and what was verified — so a
future contributor (or reviewer) can see the reasoning, not just the diff.

## Round 6 — Six concrete correctness bugs

**Feedback:** ZIP search silently does nothing (only `city` was matched);
typing `[` anywhere in a search box raised a regex error; the privacy
claim that filters "live only in the browser tab" is wrong — they run
in Python on the server; a record with `is_sample: false` but no
`source_url`/`last_verified` still displayed as "Verified"; demo
listings had live, clickable Call/Directions buttons identical to real
resources; and the free-text search box filtered the cards *after* the
result count was already printed, and the map wasn't re-filtered by it
at all — so count, cards, and map pins could disagree.

**Changes**

- Added a real `zip_code` field (the exact ZIP for each of the 8
  verified Texas entries, sourced alongside their addresses) and made
  the location filter match city **or** ZIP. It's an exact/substring
  match on the stored ZIP, not a radius search — the sidebar help text
  and the no-results message both say so explicitly, listing which
  ZIPs are actually covered.
- Added `regex=False` to every `.str.contains()` call (`apply_filters`'
  city/ZIP match and the new `apply_text_search()`), so regex-special
  characters (`[`, `(`, `*`, …) are treated as literal text instead of
  crashing.
- Reworded the privacy sections (header expander, sidebar caption,
  README) to say filter inputs are processed temporarily on the server
  to build results, and that the app does not *intentionally* persist
  them — replacing the inaccurate "exist only in the browser tab."
- Added an `is_verified` column, computed in `load_resources()` as
  `is_sample is False AND source_url AND last_verified` — not just
  `is_sample is False`. A record that's real-looking but missing
  evidence now shows a distinct "⚠️ Not verified: missing source/date"
  warning instead of silently passing as confirmed.
- Demo Data cards now render disabled "Call (disabled — demo data)"
  and "Directions (disabled — demo data)" buttons instead of live
  `tel:`/Google-Maps links.
- Refactored the in-page search into a standalone `apply_text_search()`
  and had `render_directory()` return the post-search DataFrame; `main()`
  now feeds that exact object into `render_map()`, and the displayed
  count is computed after the search, not before it — so the count,
  the cards, and the map can no longer disagree.

**Testing performed:** re-ran every prior round's automated suite (no
regressions) plus new checks for this round — ZIP '75033' and '75208'
resolving to the right orgs in the actual sidebar widget, an unlisted
ZIP correctly matching nothing, `[` in both search boxes provoking no
traceback, a synthetic "real but unevidenced" record correctly getting
`is_verified: False`, no visible live Call/Directions links anywhere in
the Demo Data tab (scoped to *visible* elements, since Streamlit keeps
inactive tabs in the DOM), and the search-then-count-then-map ordering
confirmed both by a live count check ("Promise" → exactly 1) and by
inspecting that `main()` passes `render_directory()`'s return value
into `render_map()`. One caveat: this sandbox's network policy blocks
`cdn.jsdelivr.net`, which the Folium map component loads Leaflet from,
so actual pin rendering couldn't be visually confirmed here — the fix
is verified structurally (same DataFrame object flows to both), not by
counting rendered pins.

## Round 5 — Wording, layout, and a full functional test pass

**Feedback**

1. Shorten the verification text on each card; put the full explanation
   behind an expandable link.
2. Keep prototype/demo-data details off the main introduction — the
   opening should focus on finding help.
3. Check text size at normal zoom and on mobile (a screenshot made it
   look small, though the screenshot's own scale might be the cause).
4. Give a useful no-results message: explain which filters can be
   broadened and how to clear them.
5. Then test functionality (ages 17/18/24 at the boundaries, city/ZIP +
   phone + directions + source links, demo-vs-real separation, keyboard
   nav / screen reader / 200% zoom, and real-volunteer usability
   testing) rather than adding more features. Stop redesigning once
   those pass, and document the feedback and improvements.

**Changes**

- Each verified card now shows two short lines — "✅ Address and phone
  checked *Month D, YYYY*." and "📞 Call to confirm availability and
  eligibility." — with the full explanation (what "checked" means, that
  it isn't a live-availability guarantee, and the official source link)
  moved into a "What does 'Verified' mean?" expander.
- Removed the sentence about fictional sample/demo listings from the
  main header. The opening now only covers the app's actual purpose;
  the demo-data explanation lives solely in the Demo Data tab itself,
  where it's still a prominent warning banner.
- Rewrote the empty-results message (`describe_no_results()` in
  `app.py`) to name every active narrowing filter (city/ZIP, age,
  category, walk-ins-only) and suggest a concrete way to clear or
  broaden each one, instead of a generic "try adjusting the sidebar."
- Measured text size and contrast directly rather than eyeballing them
  (see Testing below) instead of guessing at a CSS change.

**Testing performed**

All of the following were run against a live instance of the app with a
headless Chromium browser (Playwright), not just asserted:

- **Age boundaries (17/18/24):** confirmed BasePoint Academy (12–17)
  is eligible at 17 and correctly excluded at 18 and 24; confirmed
  Promise House (16–24) stays eligible at 18 and at the 24 upper
  boundary; confirmed "All Ages" resources remain visible throughout.
- **City/ZIP, phone, directions, source links:** for all 8 real
  resources — city filter surfaces the right org, the Call button's
  `tel:` href matches the org's actual phone digits, the Directions
  button points at `google.com/maps/search` with the right address, and
  (for the 4 orgs checked individually) the "Official source" link's
  `href` resolves to the organization's real domain
  (promisehouse.org, minniesfoodpantry.org, saminn.org,
  friscofamilyservices.org).
- **Demo vs. real separation:** confirmed none of the 12 fictional
  sample orgs appear in Find Resources or About & Coverage Stats by
  default, and confirmed all 12 do appear in the Demo Data tab.
- **Keyboard navigation:** walked the Tab order through the page and
  confirmed every stop is a real, accessible element (`button`, `a`,
  `input`, native `<details>/<summary>` disclosure, or a correctly
  `role="tab"` div) — never an inert `<div>`/`<span>` masquerading as
  interactive.
- **200% zoom:** applied a real `zoom: 2` (not just a narrower
  viewport) at desktop width and confirmed no horizontal overflow.
  Also checked a 390px mobile viewport separately: no horizontal
  overflow, and text is legible at 14px (see below).
- **Text size/contrast, measured:** body text (address, hours,
  eligibility, cost) is `st.markdown` (Streamlit's normal-contrast
  body text), not `st.caption` (the theme's dimmed style). Measured via
  the browser's computed styles: **12.53:1 contrast** against the page
  background (WCAG AA requires 4.5:1 for normal text) and **14px font
  size** at both 100% desktop zoom and on a 390px mobile viewport — this
  is Streamlit's own platform-wide base size, used consistently across
  the whole app, not something unique to this project.
- **Screen reader:** not tested with an actual screen reader (no
  audio-capable environment here); verified instead that every
  interactive element exposes the ARIA role and accessible name a
  screen reader depends on (`role="button"`/`"link"`/`"tab"` with a
  readable name) — a necessary but not sufficient proxy. A real
  screen-reader pass (VoiceOver/NVDA) is still worth doing before wider
  release.
- **Scripted persona scenarios** (a proxy for "ask adult volunteers to
  find a resource," which requires actual humans and can't be done by
  an AI assistant): walked through fictional cases — *"17, in Frisco,
  need someone to talk to"* → BasePoint Academy; *"20, in Dallas, need
  a walk-in shelter tonight"* → Promise House with 24/7 hours visible;
  *"need free food in Plano"* → Minnie's Food Pantry with cost shown as
  Free. All resolved correctly with the right cost/hours/access info
  visible.

**A coverage finding worth flagging, not fixing here**

The reviewer's closing note was right to separate "is 8 results a
problem" from "is coverage actually useful for what's advertised." A
scripted scenario deliberately aimed at a gap — *"need free food in
McKinney"* — surfaced one: the real dataset currently covers only 2 of
4 categories per city, in a rotating pattern:

| City     | Emergency Housing | Food Security | Legal Support | Crisis Counseling |
|----------|:---:|:---:|:---:|:---:|
| Dallas   | ✅ Promise House | — | ✅ Legal Aid NW TX | — |
| Plano    | — | ✅ Minnie's Food Pantry | — | ✅ LifePath Systems |
| McKinney | ✅ The Samaritan Inn | — | ✅ Legal Aid NW TX | — |
| Frisco   | — | ✅ Frisco Family Services | — | ✅ BasePoint Academy |

In the McKinney case the app now does the right thing — a clear,
specific empty-state message rather than silence or a crash — but that
doesn't substitute for actually having a McKinney food resource. Per the
"stop redesigning once checks pass" instruction, this round didn't add
resources to close these 8 gaps; it's recorded here as the next
concrete step, not something quietly left implicit.

---

## Round 4 — Sample-data separation, cost/access info, and honest wording

**Feedback:** keep sample/demo data out of real results by default
(preferably a separate page); add cost/appointment/referral info to
each listing; explain precisely what "Verified" checked; fix Quick
Exit's wording so it can't be read as clearing browser history; raise
the contrast on address/hours/eligibility text and measure it rather
than eyeballing it; fix a data bug duplicating the city name in some
Frisco/Dallas/Plano/McKinney addresses; stop the sidebar from pointing
"above" to a section that's actually in the main panel.

**Changes:** moved all 12 placeholder entries into a dedicated
"🧪 Demo Data (not real)" tab with no toggle back into the main flow;
added `cost`, `appointment_required`, `referral_required` to the
schema and every card; rewrote the verified badge to state exactly
what was checked and that it doesn't confirm live availability;
changed Quick Exit's caption to "Leaves this page. Does not erase
browser history."; switched the relevant text from `st.caption` to
`st.markdown`; fixed the address field to be street-only everywhere
(the city was being appended twice); reworded the sidebar privacy
caption to point at a named section instead of a spatial "above."
Verified with a 19-check pure-logic test pass and a 25-check
headless-browser pass (this also caught and fixed a real Streamlit
duplicate-element-ID bug the Demo Data tab introduced).

## Round 3 — Local relevance, trust, and honest privacy wording

**Feedback:** add real Frisco/Plano/McKinney/Dallas resources instead
of only Pacific Northwest placeholders; add a source link and
"last verified" date to every listing, and label sample data clearly;
stop claiming the sidebar filters are "not stored or sent anywhere"
when that's not really verifiable.

**Changes:** researched and added 8 real, sourced North Texas
resources across all four categories (Promise House, Legal Aid of
NorthWest Texas in Dallas and McKinney, Minnie's Food Pantry, LifePath
Systems, The Samaritan Inn, Frisco Family Services, BasePoint Academy),
each with a real address/phone and a link to the organization's own
page; added `is_sample`/`source_url`/`last_verified` fields, defaulting
to "unverified" when missing rather than silently trusted; reworded
the privacy claims to describe what the app's code actually does
(no accounts, no tracking scripts, nothing persisted) instead of an
absolute, unverifiable promise. Flagged at the time: the stored
lat/long for the new entries are hand-placed approximations, not from
a geocoding API (this environment's network policy blocks the
geocoding services that would normally produce those) — addressed in
Round 4 by adding a "🧭 Directions" link that resolves the *exact*
verified address via Google Maps at click time, independent of the
dataset's own coordinate precision.

## Round 2 — Usability structure

**Feedback:** results should come before the map and a large
introduction; "Nearby" is misleading when the filter is a multi-select
city list rather than an actual location; the three overlapping
age-range options (13–24, 16–21, 16–24) force an awkward choice instead
of just asking the user's age; the "nothing is tracked" claim needs a
real privacy section; Quick Exit needed its limits explained; the
Analytics tab needed a clearer label separating it from personal
search results.

**Changes:** moved the resource directory above the map (map now lives
in a collapsed, optional expander); replaced the city multi-select
with a free-text city/ZIP field, only saying "Near '<input>'" when one
is given; replaced the overlapping age buckets with a single age field
matched against each resource's own parsed eligibility range; added an
expandable, honest privacy disclosure; added a Quick Exit caption
explaining its limits; renamed the Analytics tab to "About & Coverage
Stats" with a caption clarifying it's dataset-wide, not personalized.

## Round 1 — Initial build

Built the initial four deliverables: `app.py` (Streamlit UI, filters,
Folium map, Plotly analytics, Quick Exit), `data/resources.json` (12
sample resources across the four categories), `requirements.txt`, and
`README.md`. Also fixed, post-deployment: a Folium tile provider that
started requiring an API key (switched to plain OpenStreetMap tiles).
