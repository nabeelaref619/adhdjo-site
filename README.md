# ADHDJO

Public Arabic and English website for ADHDJO, owned by Nabil Aref.

Production: https://adhdjo.org (GitHub Pages, main branch, repository root).

The published HTML works without a build service. The scripts maintain the
November 2026 content revision from versioned JSON and the existing page shell.
Install `scripts/requirements.txt` in a Python virtual environment, then run:

```sh
python scripts/remediate.py
python scripts/directory.py
python scripts/sources.py
python -c 'import sys; sys.path.insert(0, "scripts"); from remediate import shared_updates, sitemap; shared_updates(); sitemap()'
python scripts/media.py
python scripts/connect_media.py
python scripts/validate_site.py
python scripts/validate_media.py
```

Keep source dates truthful. Public-source verification does not establish a
clinical licence, service quality or appointment availability. Do not add a
clinical-review byline until a qualified reviewer has actually reviewed the
content and agreed to be identified. No clinical review is claimed currently.

Preserve `CNAME`, the AdSense ownership tag and `ads.txt`. Advertising is limited
to substantive guides. Directory and tool pages must not load advertising
scripts; tool answers must not be saved or transmitted by site code. Privacy
pages retain Google's tag solely to provide applicable consent controls.

The media library is maintained in `content/media.json`. It connects public
recordings and social posts to the guides. Descriptions are based on publisher
metadata and original captions, not invented transcripts. An appearance is not
a clinical endorsement. Keep publication dates distinct from event dates; omit
unknown dates. Channel links provide access to more posts, but the curated index
is not automatically synchronized or claimed to be a lifetime archive.

Media pages load no third-party media until a visitor chooses a YouTube player.
Keep external watch links usable without JavaScript, unload hidden/closed players,
and keep the privacy explanation aligned with player behavior. Do not place ads
on the media library. Do not publish private analytics, drafts or tracking tokens.
