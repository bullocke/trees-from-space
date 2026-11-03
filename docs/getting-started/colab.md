# Running in Google Colab

[Google Colab](https://colab.research.google.com/) runs notebooks on a temporary Google-hosted machine, with nothing to install on your computer. It suits the small lesson examples. CHPC remains the main platform for longer or larger work, because a Colab session has limited memory and stops after a period of inactivity or a maximum run time.

> **Validation status.** A lesson is advertised for Colab only after it runs from start to finish in a fresh Colab session. The [tutorial index](../tutorials/README.md) shows which lessons have passed. Lessons without a Colab result may still work, but nobody has confirmed it.

## Opening a lesson

Lessons that passed in Colab have an **Open in Colab** badge in their README. To open any other notebook from the repository, replace `https://github.com/` in the notebook's GitHub address with `https://colab.research.google.com/github/`.

## What differs from CHPC and your own computer

- **Installation.** Colab already includes many scientific packages. The first code cell of each lesson detects Colab and installs the remaining packages with pinned versions, which takes a minute or two. You do not need to create an environment.
- **Files.** The notebook runs without the rest of the repository, so lessons keep the settings they need inside the notebook. The `cache/` and `outputs/` folders are created under `/content`. Everything under `/content` is deleted when the session ends, so download results you want to keep from the file browser in the left sidebar (right-click a file, then *Download*).
- **Credentials.** Each session starts without your `~/.netrc`. When a lesson needs to read NASA data, it asks for your Earthdata username and password once and saves them to a `~/.netrc` that disappears with the session.

## Using Colab Secrets instead of typing your password

Colab's **Secrets** panel (the key icon in the left sidebar) stores values in your Google account and makes them available to your notebooks. Add two secrets, `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD`, and allow the notebook to access them when asked. The lessons look for these secrets before prompting. Secrets stay attached to your account and are not shared when you share a notebook.

## R in Colab

Colab can run R notebooks (*Runtime → Change runtime type → R*), but installing geospatial R packages such as `terra` and `sf` in a fresh session can take a long time. Use CHPC or your own computer for the R lessons. The index shows any R lesson that has been validated in Colab.
