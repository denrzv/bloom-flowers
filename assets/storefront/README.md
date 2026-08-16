# Storefront artwork

Bloom Flowers keeps all storefront imagery in this directory so the demo remains inspectable, same-origin and dependency-light.

## BLOOM-005 generated imagery

The primary showcase images are original AI-generated demo artwork produced specifically for Bloom Flowers, then curated and optimized for repository use. They are committed with the site and served from the Bloom origin; no image CDN, hotlink, runtime generation service, embedded remote reference, tracker, hosted font or other third-party dependency is required.

Files used by the current storefront:

- `hero-bouquet.webp` — portrait pink/peach/cream hero arrangement in a blush vase.
- `happy-days.webp` — canonical Happy Days product image used by Popular Picks and the product page.
- `garden-party.webp` — cream/yellow/blush bouquet for Popular Picks and related products.
- `sunset-peonies.webp` — coral/peach/warm-pink bouquet for Popular Picks and related products.
- `happy-days-detail-1.webp` — close-up floral crop for the Happy Days gallery.
- `happy-days-detail-2.webp` — alternate side/vase view for the Happy Days gallery.
- `happy-days-detail-3.webp` — wrapped, delivery-ready Happy Days presentation.

## BLOOM-006 generated catalog plants

BLOOM-006 completes the catalog image language with three generated houseplant product images using the same soft cream/blush studio direction as the bouquet set:

- `desk-plant-duo.webp` — two easy-care indoor plants in blush and cream ceramic pots.
- `trailing-pothos.webp` — lush trailing pothos in a blush ceramic pot.
- `small-cactus-set.webp` — pastel three-pot cactus/succulent set.

The WebP exports are intentionally sized for the static mobile-first demo rather than shipped at raw generation resolution. Consuming HTML declares each image's intrinsic dimensions so the browser can reserve layout space before decode.

## BLOOM-004 vector artwork

The earlier project-owned SVG set remains in the repository as fallback/reference artwork and as a record of the BLOOM-004 visual pass:

- `hero-bouquet.svg`
- `happy-days.svg`
- `happy-days-close.svg`
- `happy-days-side.svg`
- `happy-days-wrap.svg`
- `garden-party.svg`
- `sunset-peonies.svg`

These assets are presentation-only. Product names, prices, fulfilment information and navigation remain available as text and do not depend on colour or imagery. SiteSkin discovery, manifest ownership and browser trust surfaces are unchanged by the storefront artwork.
