# ADHDJO advertising setup

Updated 17 October 2026.

- Production website: https://adhdjo.org (GitHub Pages, `main`, repository root).
- Publisher: `ca-pub-3422496043906198`.
- Ownership tag and root `ads.txt` are published. AdSense reports ads.txt as Authorised.
- Review requested on 17 October 2026. AdSense reports Getting ready; approval is pending.
- Manual responsive ad unit: `9493301422`, "ADHDJO - below content - responsive".
- One labelled below-content placement on each English/Arabic home, FAQ, learn overview, and five article pages: 16 pages in total.
- Google AdSense tag is also present on the three privacy-page URLs to provide privacy controls, without an ad placement there.
- `requestNonPersonalizedAds=1` is set before loading the tag. The tag also uses `data-privacy-treatments="disablePersonalization"`.
- Interactive tools, the support directory, language selector, sources, about and contact pages have no ad-serving scripts. Do not add advertising tags or tracking to pages that accept private tool text.
- Tool answers and local learning progress are never included in advertising requests by site code.
- Auto ads was OFF for adhdjo.org when checked. Keep it off to preserve the manual placements and exclusions. The separate studioirth.com settings were not changed.
- Published Google messages: "ADHDJO privacy choices" (European regulations, consent/refusal/manage options, reject enabled across all covered regions, message optimisation off) and "ADHDJO US privacy choices" (all current and future supported US states).
- Both Google message editors use English. The website privacy notices are in Arabic and English; Google message languages are separate from website languages.
- European consent revocation uses `assets/js/ads-privacy.js` and Google's documented callback API. Google's US message supplies its own opt-out link.
- Privacy policy URL in AdSense: https://adhdjo.org/en/privacy/.
- No visitor-analytics service was added as part of this change.

The website is static source, with no build step. Preserve `CNAME`, `ads.txt`, and existing bilingual URLs. Every advertising change must retain the personalization safeguards and accurate privacy notices. Google controls review approval and ad availability; a valid setup does not guarantee either.

References:
- https://support.google.com/adsense/answer/7670312
- https://developers.google.com/funding-choices/fc-api-docs

Validation: JavaScript syntax, advertising scope, privacy safeguards, local links, schema and sitemap parse checks. Live ad serving is not yet verifiable because site approval is pending.
