# Shuttle Rank — design system

Visual language for every page in `docs/ux/pages.md`. Implement with Tailwind and shadcn/ui. Do not add a second component library or a chart library besides Recharts.

Reference image: `docs/Design/reference-dashboard.webp` (a dark TENOIS tennis dashboard). Borrow its density and chrome. Do not copy its sport, its photo, or its marketing stats.

## What to take from the reference

- Full dark UI, rounded cards, 1px quiet borders, no drop-shadow stack.
- Compact pill navigation and a pill search field.
- A hero row: a large left card and a highlighted right card.
- Big tabular numbers with a 12px label under them.
- Small chips for status and for W / L.
- A chart card whose tooltip is a small dark chip, not a browser default.
- A dense ranked table: two-digit rank, avatar, name, numbers, one row link.
- Lime used as the primary action, not as a page wash.

## What to change

| Reference | Shuttle Rank |
|---|---|
| Court photograph and location line | Club hero: wordmark, latest real result, three counts. No stock photo, no map pin. |
| "Top Pick" player photo and quote | Leader card: Elo, record, form, link to the profile. Initials or `avatar_url`. |
| Audience engagement bars, "Last 09 weeks" | Line chart of Elo from the 1500 start. No invented time-window control. |
| Player comparison, country, brand score, market value | Club leaderboard: Elo, W–L, win rate, last change. |
| Bell, settings, user avatar | Omitted on the public site. Visitors have no account. |
| Sky-blue frame around a floating window | Full-bleed `#090B0A`. The page is the product, not a mock on a photo. |
| White text on a lime button | Forbidden. Lime fills use `#090B0A` text. |

The app name is **Shuttle Rank**. There is no TENOIS wordmark.

## Color

| Token | Hex | Role |
|---|---|---|
| `bg` | `#090B0A` | Page background |
| `surface` | `#171A18` | Cards, header, dialogs |
| `elevated` | `#222623` | Hover rows, active nav pill, skeleton, dropdowns |
| `border` | `#2C312E` | 1px card and row borders |
| `text` | `#F5F7F5` | Primary text |
| `text-muted` | `#A1AAA3` | Labels, ranks, secondary numbers |
| `lime` | `#A6F36B` | Primary button fill, positive delta, active nav text, leader series |
| `cyan` | `#35D5D0` | Focus ring, in-progress and ready chips, second chart series |
| `coral` | `#F2706B` | Negative delta, destructive button fill, error border |
| `amber` | `#E8B84A` | Disputed status only |

No gradients, glows, or blurred color orbs. A card may use a 1px `border` and, for the admin shell only, a 2px lime top border on the header.

**Pairings.** These are the allowed text/fill pairs. Contrast is approximate, calculated against the hex above, and each pair is meant to clear WCAG AA for normal text:

- `#F5F7F5` on `bg`, `surface`, and `elevated` is far above AAA.
- `#A1AAA3` on `bg` is about 8:1. Do not put muted text on lime, coral, or amber fills.
- `#A6F36B` as text on the three dark surfaces is about 12:1. A lime **button** is `#A6F36B` fill with `#090B0A` text (about 14:1). Never set `#F5F7F5` on lime.
- `#F2706B` as text on `bg` is about 7:1. A destructive button is coral fill with `#090B0A` text.
- `#E8B84A` as text on `bg` is about 10:1. Use it for the disputed label, not as a large fill.
- `#35D5D0` as text or as the focus ring on the dark surfaces stays above 7:1. Do not put cyan text on a lime button.

## Type

Geist Sans, the Next.js default. Fallback: `ui-sans-serif, system-ui, sans-serif`.

| Style | Size / line | Weight | Use |
|---|---|---|---|
| Display | 56 / 56 | 600 | Hero Elo on the leader card |
| Title | 28 / 34 | 600 | Page title |
| Card title | 18 / 24 | 600 | Card headings |
| Body | 14 / 20 | 400 | Copy, names, table text |
| Label | 12 / 16 | 500 | Stat labels, table headers, eyebrows |

Labels are sentence case ("Matches", "Win rate"), not tracking-heavy capitals. Every rank, Elo, W–L, percent, and delta uses `font-variant-numeric: tabular-nums`.

## Spacing, radius, elevation

4px grid. Use 4, 8, 12, 16, 20, 24, 32, 48.

- Page padding: 16px below 768px, 32px from 768px up.
- Content max width 1120px, centered.
- Card padding: 16px below 768px, 20px from 768px up.
- Grid gap: 16px below 1024px, 20px from 1024px up.
- Radius: cards and dialogs 20px; the dashboard hero and leader card 24px; inputs 12px; buttons, nav pills, chips, and search fully rounded.
- Elevation is a lighter surface, not a shadow. Clickable cards on hover lighten the border to `#3A403C`.

## Card anatomy

1. Eyebrow, 12px muted (optional).
2. Title row: card title on the left, one text action or chips on the right.
3. Body.
4. Stat strip when needed: number in 28–40px, label in 12px muted directly under it.

Public cards that navigate have a real link around the row or a visible text button. A lone icon is not the action.

## Table anatomy

Wrapped in a surface card. Header is 12px muted. Minimum row height 56px. Hairline `border` between rows. No zebra.

- Rank: two digits, muted, tabular, left.
- Avatar 28px circle, or initials (first letters of the first two words, uppercased) on `elevated`.
- Elo: 16px tabular.
- Numeric columns right-aligned. Player name left-aligned.
- Hover row: `elevated`.
- Public data rows are one link to the profile or the match. No kebab menu.

**Below 768px** the leaderboard, monthly board, and match list become cards: rank and name on the first line, Elo at the right, second line W–L, win rate, delta, and form. Admin tables stay tables inside a horizontal scroller; the name column is sticky. The page itself does not scroll sideways.

## Charts

Recharts line chart, one card.

- Leader series `#A6F36B`. Then `#35D5D0`, `#F5F7F5`, `#C8D4A8`, `#A1AAA3`.
- Stroke 2px. Dots radius 0 until hover, then 4. No area fill.
- Grid and axis lines `#2C312E`. Tick labels 12px muted. Y domain padded around the data, never forced to 0.
- Tooltip: `elevated` background, radius 12, 1px border. Dashboard tooltip: player, date (or "Start"), rating. Profile tooltip: date, opponent, W or L, new rating, signed delta. Values come from the payload.
- Legend buttons toggle a series. The leader starts visible; if five lines are noisy the user can isolate one.
- `prefers-reduced-motion`: render the line with no animation.
- Under the chart, one text summary for assistive tech: the leader's latest rating and last signed change, from fields already on the page.

## Iconography

Lucide, stroke 1.75. 16px in the nav, 18px beside a button label. The icon never replaces the label on a button.

| Place | Icon |
|---|---|
| Wordmark mark | 8px lime disc. No custom SVG required. |
| Dashboard | `LayoutDashboard` |
| Leaderboard | `ListOrdered` |
| Players | `Users` |
| Matches | `History` |
| Head-to-head | `GitCompare` |
| Tournaments | `Trophy` |
| Search | `Search` |
| Admin shell | `Shield` |
| Achievements | `Award` |
| Audit | `ScrollText` |
| Add / record | `Plus` |
| Edit | `Pencil` |
| Deactivate | `UserX` |
| Correct | `RotateCcw` |
| Cancel match | `XCircle` |
| Delete | `Trash2` |
| Open public page | `ArrowUpRight` |
| Positive delta | `TrendingUp` |
| Negative delta | `TrendingDown` |
| Champion | `Crown` |
| Unknown badge icon | `Award` |

## Rating and record language

One shared treatment everywhere:

| Value | Text | Color |
|---|---|---|
| Delta > 0 | `+16` and `TrendingUp` | lime |
| Delta < 0 | `−16` (U+2212) and `TrendingDown` | coral |
| Delta = 0 | `0` | muted |
| Delta null / unrated | `—` | muted |
| Win rate null | `—` | muted |
| Win rate set | `50.0%` from the 0–1 float | text, muted when it sits beside Elo |
| W–L | `12–7` with an en dash | text, tabular |
| Form `W` | chip "W" | lime text on lime at 16% opacity |
| Form `L` | chip "L" | coral text on coral at 16% opacity |

Form chips are oldest on the left. The payload's index 0 is the rightmost chip. An empty `recent_form` shows no chips.

## Status chips

12px text, pill, 16% tint of the ink color on the dark card.

| Status | Ink | Label |
|---|---|---|
| `in_progress` | cyan | In progress |
| `draft` | muted | Draft |
| `completed` (tournament or match, when the filter is not already "completed") | lime | Completed |
| `canceled` | muted | Canceled |
| `disputed` | amber | Disputed |
| `bye` | muted | BYE |
| `ready` (admin bracket only) | cyan | Ready |
| `pending` | muted | Waiting |
| Player inactive | muted | Inactive |
| Match deleted (admin only) | coral | Deleted |
| `auth_mode: dev` | amber | Dev auth |

## Loading, empty, error

- **Loading.** Skeletons are `elevated` blocks with radius 8 on the `surface` card, matching the final layout. No full-page spinner. The header stays put.
- **Empty.** One sentence in body text, muted. No illustration. If an admin action would fill the region, one primary button.
- **Error.** The region becomes a card with a 3px coral left border, the sentence "Couldn't load {thing}.", and a Retry button (secondary). Network failure copy is "Couldn't reach Shuttle Rank. Try again."
- **Not found.** "{Thing} isn't on Shuttle Rank." and a text link to the parent list.
- **Validation.** Under the field, or `error.message` at the top of the dialog. Dialogs stay open on failure.

Empty sentences are written per page in `docs/ux/pages.md`.

## Controls

- **Primary:** lime fill, `#090B0A` label, pill, height 40px (44px min tap below 768px).
- **Secondary:** transparent, 1px `border`, `#F5F7F5` label, pill.
- **Destructive:** coral fill, `#090B0A` label, pill. Used only for delete, deactivate, cancel match, and revoke.
- **Focus:** 2px `#35D5D0` outline, 2px offset, on every interactive element including the lime button. Do not remove the outline without this ring.
- **Dialog:** `surface`, radius 20, padding 24, max width 440px. Title, body, then actions aligned to the end: secondary Cancel, then primary or destructive. Initial focus is the Cancel button. Esc cancels. Enter does not confirm. Focus is trapped until the dialog closes.
- **Touch targets** below 768px are at least 44px. Body text stays 14px.

## Breakpoints and navigation

| Width | Layout |
|---|---|
| 0–767 | Single column. Public **bottom bar**: Dashboard, Leaderboard, Players, Matches, More. More opens Head-to-head and Tournaments. Header is the wordmark plus the search icon. |
| 768–1023 | Single column, page padding 32px. Header pills wrap to a second row. No bottom bar. |
| 1024 and up | Primary design. Header: wordmark, pill links (Dashboard, Leaderboard, Players, Matches, Head-to-head, Tournaments), search pill. No bottom bar. Grids in `pages.md` apply. |

Active pill: `elevated` background, lime text. Inactive: muted text. Sticky header, 64px, `surface`, bottom border `border`.

**Search.** Opens a listbox. On open, load `GET /players` once (active only) and filter locally by name. Arrow keys move, Enter opens the profile, Esc closes. Empty query lists the directory. No match: "No player found."

**Admin shell.** Same tokens. Header: Shield, "Admin" lime chip, links to Overview, Players, Matches, Tournaments, Achievements, Audit, then "View site" (`ArrowUpRight`) and the email. A 2px lime line sits on top of the header. No public bottom bar. Below 768px the admin links wrap into a second row; they do not share the public tab bar.

## Motion and accessibility

- Transitions are color and border only, 120ms. No page transitions, no count-up animations.
- Honor `prefers-reduced-motion`.
- Landmarks: one `header`, one `main`, one `nav`, one `footer`. A "Skip to content" link is the first focusable control.
- Chart series are not identified by color alone; the legend prints the name.
- Dialogs and icon-only controls (the mobile search icon) have accessible names.
- Status is text, not only a colored dot.
- `lang` is `en`.
