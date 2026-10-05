# website

Personal website of Atsuhisa Ota, served by GitHub Pages from `master`,
in English (`index.html`), Japanese (`ja/`) and Simplified Chinese (`zh/`).

## Editing

Do not edit `index.html`, `ja/index.html` or `zh/index.html` directly: they are generated.

| File | What it holds |
|---|---|
| `_src/page.html` | Page template: `{{t:key}}` for text, `{{b:name}}` for generated blocks |
| `_src/strings.yaml` | All text of the site in en / ja / zh |
| `_src/cv.yaml` | Japanese and Chinese names of the CV items that come from `mycv` |
| `assets/` | Styles, scripts |

Folders starting with `_` are not published by GitHub Pages.

## Building

Positions, memberships, grants, teaching and the full list of talks come from the
private `mycv` repository. With `mycv` checked out next to this repository:

```sh
pip install pyyaml
python3 scripts/build_site.py ../mycv
```

This writes the three pages. It writes only public fields of `mycv`: no internal notes,
sources, grant numbers, amounts or project titles, and it skips the funding entries in
`HIDDEN_FUNDING`. It prints a warning when a CV item has no translation in `_src/cv.yaml`.

The publication list is loaded in the browser from INSPIRE-HEP and needs no update.
Publication data and talk data are shown in English in all three languages.
