# Bloom Flowers

The reference integration for **SiteSkin**, an open protocol that lets a website describe its own
navigation and branding so a browser can render them as native chrome.

Bloom Flowers is a fictional shop. It exists to be a real website that a SiteSkin browser can be
pointed at — and to be small enough to read end to end.

- **Live site:** <https://denrzv.github.io>
- **The whole integration:** [`.well-known/siteskin.json`](.well-known/siteskin.json) — one file
- **How to do this to your own site:** [`INTEGRATION.md`](INTEGRATION.md)
- **The protocol:** [`SPEC.md`](https://github.com/denrzv/webora/blob/main/spec/SPEC.md) in
  `denrzv/webora`

## What is in here

```
.well-known/siteskin.json   the integration, byte-identical to webora's conformance fixture
index.html catalog/ cart/ account/   a plain static site, no framework, no build step
assets/site.css             one stylesheet
assets/siteskin/logo.png    the brand asset the manifest points at
tools/make-logo.py          regenerates that logo, standard library only
tools/check-routes.py       asserts the site serves every path the manifest names
```

There is nothing to install and nothing to build. Serve the directory:

```bash
python3 -m http.server 8000
```

## Where this is deployed, and why not from here

The site is published by **[`denrzv/denrzv.github.io`](https://github.com/denrzv/denrzv.github.io)**,
whose workflow checks this repository out at deploy time. There is deliberately no Pages deployment
in *this* repository.

The reason is the protocol's, not a preference. SiteSkin discovery requests
`/.well-known/siteskin.json` at the **origin root**, and this manifest's paths (`/catalog`, `/cart`,
`/account`) are origin-absolute. A GitHub Pages *project* site is served from a subpath, where that
well-known path belongs to whoever owns the user-site root and every manifest path resolves outside
the deployment — so a project page cannot host a SiteSkin integration at all. A user site owns its
root, so that is where the demo lives.

`denrzv.github.io` is a stopgap. A dedicated domain is the intended home; it also cannot supply the
several distinct origins a multi-site demo would need.

## The manifest is a copy

`.well-known/siteskin.json` is not authored here. It is byte-identical to
`spec/fixtures/valid/bloom-flowers.json` in `denrzv/webora`, which is the conformance fixture the
SiteSkin validator is written against, and the copy direction is one way.

Both repositories pin the same SHA-256 — this one in
[`.well-known/siteskin.json.sha256`](.well-known/siteskin.json.sha256), the other in its test suite
— so editing either side alone breaks that side's own build immediately. Changing the manifest means
changing both, in the same change.

## Not a real shop

No cookies, no analytics, no storage, no forms, and no requests to any other origin. Nothing is for
sale and no page collects anything.
