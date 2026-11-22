# Ochoa TV catalog

Public content catalog for the Ochoa TV Fire TV app (Mexican live TV, films,
series and sports). This repository contains **only catalog data**. No app
code, keys or personal data.

- `manifest.json`: names the active release (`version`, `catalog` file).
- `catalog-<version>.json`: a complete, validated release. Old releases are kept for rollback.
- `channels.json`, `vod.json`: readable copies of the active release's data.

The app reads `manifest.json` from GitHub Pages, downloads the release it names,
validates it completely and only then switches to it. If anything fails, it keeps
its last working catalog.

Every entry is a public stream or video published by its rights holder, with the
evidence recorded in `originEvidence`. Nothing is hosted here except metadata.
