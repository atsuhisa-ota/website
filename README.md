# website

Personal website of Atsuhisa Ota, served by GitHub Pages from `master`.

## Updating the CV and talks

Memberships, grants, teaching and the full list of talks are generated from the
private `mycv` repository. With `mycv` checked out next to this repository:

```sh
pip install pyyaml
python3 scripts/build_cv.py ../mycv
```

The script rewrites the blocks between `<!--NAME:START-->` and `<!--NAME:END-->`
in `index.html`. It writes only public fields: no internal notes, sources,
grant numbers, amounts or project titles.

The publication list is loaded in the browser from INSPIRE-HEP and needs no update.
