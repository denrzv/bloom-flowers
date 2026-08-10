# Add SiteSkin to your site in fifteen minutes

**SiteSkin** is an open protocol that lets a website describe its own navigation and branding so a
browser can render them as native app chrome — a branded top bar, a bottom navigation bar, quick
actions — around your existing pages.

You add one file. You change nothing else. Every browser that has never heard of SiteSkin ignores
the file completely, and your site behaves exactly as it does today.

This repository is the reference integration. Everything described below is live in it, and you can
read the whole thing: [`.well-known/siteskin.json`](.well-known/siteskin.json) is the entire
integration, and the four HTML pages beside it are an ordinary static site with no build step.

> The specification is [`SPEC.md`](https://github.com/denrzv/webora/blob/main/spec/SPEC.md) in
> `denrzv/webora`. You should not need it. It is written for someone implementing a browser; this
> document is written for someone who owns a website.

---

## 1. The five-minute version

Create `/.well-known/siteskin.json` at the root of your site:

```json
{
  "schemaVersion": "1.0",
  "site": {
    "id": "bloom-flowers",
    "name": "Bloom Flowers"
  }
}
```

That is a complete, valid manifest. Three fields are required — `schemaVersion`, `site.id` and
`site.name` — and everything else is optional with a browser-chosen default.

Publish it over HTTPS. That is the integration.

### Where the file goes, and why it is not negotiable

The path is exactly `/.well-known/siteskin.json`, at the **root of your origin**:

```
https://your-site.example/.well-known/siteskin.json   ✅
https://your-site.example/siteskin.json               ❌ never requested
https://pages.example/your-site/.well-known/…         ❌ wrong origin
```

A browser fetches this one path and nothing else — there is no `<link>` tag to add and no HTML to
change, so a manifest cannot be injected by anything that can inject markup into your pages.

The practical consequence is worth knowing before you start: **a project-style hosting URL cannot
serve a SiteSkin integration.** If your site lives at `username.github.io/my-project/`, the origin
root belongs to whatever is deployed at `username.github.io/`, and your manifest is never
requested. You need your own domain, or a user/organisation site that owns its origin root. This
repository uses a custom domain for exactly that reason — see [`CNAME`](CNAME).

---

## 2. The full reference manifest, block by block

Here is the complete file this site publishes. Each block is optional; each is explained below.

```json
{
  "schemaVersion": "1.0",
  "site": {
    "id": "bloom-flowers",
    "name": "Bloom Flowers",
    "shortName": "Bloom",
    "homeUrl": "/"
  },
  "branding": {
    "primaryColor": "#D94F8A",
    "secondaryColor": "#FADADD",
    "backgroundColor": "#FFF7FA",
    "textColor": "#2B1B24",
    "logoUrl": "/assets/siteskin/logo.png"
  },
  "toolbar": {
    "title": "Bloom Flowers",
    "subtitle": "Fresh flowers delivered today"
  },
  "bottomNavigation": [
    {
      "id": "home",
      "label": "Home",
      "icon": "home",
      "action": { "type": "internal_url", "url": "/" },
      "match": ["/"]
    },
    {
      "id": "catalog",
      "label": "Catalog",
      "icon": "grid_view",
      "action": { "type": "internal_url", "url": "/catalog" },
      "match": ["/catalog", "/catalog/**"]
    }
  ],
  "quickActions": [
    {
      "id": "call-shop",
      "label": "Call",
      "icon": "call",
      "action": { "type": "phone", "value": "+10000000000" }
    }
  ]
}
```

### `site` — who you are

| Field | Required | Notes |
|---|---|---|
| `id` | yes | A stable identifier for your integration. Not shown to users. |
| `name` | yes | Your site's name. |
| `shortName` | no | Used where space is tight. |
| `homeUrl` | no | Where the Home action goes. Must be inside your origin. Defaults to `/`. |

### `branding` — colours and a logo

Four colours as `#RRGGBB` or `#RGB`, and one logo URL.

**Your colours are a request, not an instruction.** The browser runs a contrast check over every
pair it forms and corrects anything that would be unreadable — WCAG AA, 4.5:1 for body text and
3:1 for interface elements. Choose a hostile combination and you do not get an unreadable browser;
you get a corrected one. This site's stylesheet does the same arithmetic on itself, so the page and
the native chrome agree: see the comment at the top of [`assets/site.css`](assets/site.css), where
white-on-`#D94F8A` at 3.86:1 is darkened for body text rather than shipped.

**The logo has a budget**, and it is checked before anything is decoded:

| Constraint | Value |
|---|---|
| Format | PNG or WebP. **SVG is always refused.** |
| Bytes | at most 512 KiB |
| Dimensions | at most 1024 px per axis, and 1,048,576 px in total |
| Origin | same origin as the manifest. A CDN URL will not load. |

The declared format must match the file's actual bytes — the browser reads the signature, not the
file extension. Your logo is drawn into a small fixed slot beside your site's domain, so a large
image buys nothing; this site ships a 512×512 PNG of about 5 KB, generated by
[`tools/make-logo.py`](tools/make-logo.py).

If the logo cannot be fetched or decoded, you get a generated monogram instead. Nothing breaks.

### `toolbar` — the text in the top bar

`title` (64 characters) and `subtitle` (128). Longer strings are truncated, not rejected.

### `bottomNavigation`, `quickActions`, `menu` — what people can tap

Up to **5** navigation items, **5** quick actions and **20** menu items. Over the limit, the extras
are dropped and the rest still works.

Each item is an `id`, a `label` (32 characters), an optional `icon`, an `action`, and an optional
`match`.

`icon` is a name from a browser-provided set, never a URL — the format only accepts
`^[a-z][a-z0-9_]{0,31}$`, so an icon field structurally cannot carry a resource reference. Webora
currently draws `home`, `grid_view`, `shopping_cart`, `person` and `call`; anything else falls back
to a generic glyph and reports a warning. It does not reject your manifest.

---

## 3. Actions — the complete list

There are nine, and there will never be an arbitrary tenth. This is an allow-list.

| `type` | What happens | Field |
|---|---|---|
| `internal_url` | Navigates your site | `url`, inside your origin |
| `external_url` | Leaves your site, after the browser asks the user | `url`, HTTPS only |
| `phone` | Opens the dialer with the number filled in | `value` |
| `email` | Opens the mail composer | `value` |
| `map` | Opens a location | `value` |
| `share` | Opens the system share sheet for the current page | — |
| `home` | Goes to your `site.homeUrl` | — |
| `refresh` | Reloads | — |
| `open_menu` | Opens the SiteSkin menu | — |

**An unknown action type drops that one item and keeps the rest of your manifest.** This is
deliberate: a site experimenting with a future action should not lose its whole integration over
it.

Only four URI schemes are ever accepted anywhere in the format: `https`, `mailto`, `tel`, `geo`.
`javascript:`, `file:`, `content:`, `intent:` and `data:` are refused — as is anything else, since
this is an allow-list and not a list of known-bad values.

---

## 4. Active state: the `match` block

`match` tells the browser which of your tabs to highlight for the page someone is on. It is a list
of path patterns, and the grammar is deliberately tiny:

| Token | Matches |
|---|---|
| `*` | any characters **within one path segment** — never a `/` |
| `**` | zero or more **whole** segments |
| anything else | itself, literally |

There are no regular expressions, no character classes and no `{a,b}` alternation. A pattern from
an untrusted source invites catastrophic backtracking, and the mitigation costs more than this
grammar does.

Resolution is deterministic:

1. An exact literal match beats any pattern match.
2. Otherwise, the pattern with the longest literal prefix wins.
3. Otherwise, the item that appears first wins.
4. **If nothing matches, no tab is highlighted.** The browser will not fall back to selecting your
   first item.

### The mistake this reference site made

Until recently the `home` entry above had no `match` at all. `match` is optional and everything
validated cleanly — but rule 4 means that on this site's own landing page, *no* tab was
highlighted. Valid manifest; wrong description of the site.

If you take one thing from this section: **give every navigation item a `match`, including the one
that points at `/`.**

### Trailing slashes

Note that `**` matches *zero* or more segments, which is easy to misread. `"/cart/**"` matches
`/cart` as well as `/cart/` and `/cart/anything` — a trailing `**` is satisfied by an already
complete path. That matters because most static hosts redirect `/cart` to `/cart/`, and your
patterns need to cover whichever spelling the browser ends up on.

---

## 5. Check your work

```bash
git clone https://github.com/denrzv/webora
cd webora
./gradlew :siteskin-lint:run --args="https://your-site.example"
```

Pass the **origin only** — scheme and host, no path. The tool appends `/.well-known/siteskin.json`
itself, follows at most two same-origin redirects, and runs the exact validator the browser runs.

| Exit code | Meaning |
|---|---|
| `0` | Your manifest is accepted. Warnings and dropped items may still be reported — they do not stop your integration from working. |
| non-zero | Either the manifest was rejected, or the tool could not reach it (DNS, TLS, HTTP, or a usage error). The two are reported differently. |

Diagnostics are codes like `SS-E-ORIGIN-MISMATCH` or `SS-W-CONTRAST-CORRECTED`, each with a JSON
pointer to the field that produced it, so `/bottomNavigation/2/action/url` tells you precisely which
item to look at.

Codes beginning `SS-E-` are errors and `SS-W-` are warnings — but read the reported disposition
rather than the prefix. `SS-E-ACTION-UNKNOWN`, for instance, is an error that drops one item and
leaves the rest of your manifest working.

This repository also runs an offline check in CI ([`tools/check-routes.py`](tools/check-routes.py))
that asserts every path the manifest names is actually served. The validator can tell you your URLs
are well-formed and same-origin; only your own filesystem can tell you they are not 404s. Copying
that idea is worth fifteen more minutes.

---

## 6. What the browser will refuse

None of these break your site. Every one of them ends with the visitor on your page in an ordinary
browser, which is the entire failure model: **an invalid manifest is indistinguishable from no
manifest.**

| You publish | What happens |
|---|---|
| Over plain HTTP | No SiteSkin. HTTPS is required. |
| A manifest over 128 KiB | Rejected before parsing. |
| An unknown **major** version (`2.0`) | Rejected. Minor versions are forward-compatible. |
| A URL pointing off your origin in `internal_url` | That item is dropped. |
| A logo on a subdomain or a CDN | The logo is dropped; you get a monogram. Subdomains are not the same origin and are not trusted. |
| An unknown action type or icon name | That item is dropped, or the icon falls back. The rest applies. |
| Unrecognised fields | Ignored, reported as `SS-W-FIELD-UNKNOWN`. |
| Over-limit lists or strings | Truncated, with a warning. |

---

## 7. What a manifest never grants

As important as the list above, and easier to get wrong by assuming:

- **No operating-system permission.** A `phone` action opens the dialer with your number filled in.
  It does not gain permission to place a call, and no manifest field can ask for one.
- **No access to your pages' contents.** SiteSkin describes navigation and branding. It does not
  read the DOM, what a visitor types, or what your server stores.
- **No code execution.** The manifest is data. There is no script field, no bridge into the page,
  and no way for a manifest to run anything.
- **No cross-origin reach.** Assets are same-origin only. Subdomains are separate origins and are
  not trusted automatically.
- **No control of the browser's own identity chrome.** Your site's registrable domain and its
  TLS indicator stay visible whenever your branding is applied, in the browser's own typography, and
  no field can hide, restyle or move them. There is no `showDomain`, and there will not be one — the
  reasoning is in
  [`ADR-006`](https://github.com/denrzv/webora/blob/main/docs/adr/ADR-006-browser-owned-security-chrome.md).
  Your logo and title sit *beside* your domain, never instead of it.
- **No automatic activation.** The first time your manifest validates, the browser asks the visitor
  whether to apply it, showing your full origin. They can decline, permanently, per site. You cannot
  pre-authorise yourself, and a visitor can switch SiteSkin off globally at any time.

If that list reads as a set of limitations, it is the right way round: they are what makes it safe
for a browser to render your navigation as though it were the browser's own.

---

## 8. Checklist

- [ ] `/.well-known/siteskin.json` served from your origin root, over HTTPS
- [ ] `schemaVersion`, `site.id`, `site.name` present
- [ ] Every `internal_url` inside your own origin
- [ ] A `match` on every navigation item — including the one pointing at `/`
- [ ] `match` patterns cover the trailing-slash form your host actually serves
- [ ] Logo same-origin, PNG or WebP, within the size and dimension budget
- [ ] `siteskin-lint` exits 0 against your live origin
- [ ] Every path the manifest names actually resolves on your site

---

## Licence and reuse

Copy this manifest, this checklist and `tools/check-routes.py` into your own site freely. That is
what a reference integration is for.
