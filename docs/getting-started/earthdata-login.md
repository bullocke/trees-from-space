# NASA Earthdata Login

Most lessons read NASA data, which requires a free Earthdata Login account. Searching NASA's catalog works without one, but downloading or reading files does not.

## 1. Create an account

Register at [urs.earthdata.nasa.gov](https://urs.earthdata.nasa.gov/users/new) and confirm your email address. Keep your username and password at hand for the next step.

## 2. Store your credentials in `~/.netrc`

The lessons, the Python and R geospatial libraries, and batch jobs all read your credentials from one file, `~/.netrc`, in your home directory. You create it once on each system you use (your computer, CHPC, or a Colab session). Your password never appears in a notebook.

**Option A: let `earthaccess` write the file.** On a machine with internet access (on CHPC, a login node), activate the Trees from Space Python environment and run:

```bash
python -c "import earthaccess; earthaccess.login(strategy='interactive', persist=True)"
```

Enter your username and password when prompted. `earthaccess` checks them with NASA and saves them to `~/.netrc`.

**Option B: write the file yourself.** Create `~/.netrc` in a text editor with these three lines, using your own username and password:

```
machine urs.earthdata.nasa.gov
    login <your-username>
    password <your-password>
```

Then make it readable only by you:

```bash
chmod 600 ~/.netrc
```

The getting-started notebook confirms that the file exists, that only you can read it, and, where the network allows, that NASA accepts the credentials. It never prints them.

## Using R

The R lessons use the same `~/.netrc`, through GDAL options set at the top of each notebook. They do not need the `earthdatalogin` package. If you use it elsewhere, do not call `earthdatalogin::edl_netrc()` or `edl_search()` without your own username and password: when they find no credentials in the package's own location, they write a shared public account and point GDAL at it, so your data requests would no longer use your account.

## Using Colab

A Colab session starts with an empty home directory. The lessons detect Colab and, when needed, ask for your username and password once per session. `earthaccess` then writes `~/.netrc` inside that temporary session, which disappears when the session ends. See the [Colab guide](colab.md) for an option that uses Colab's Secrets panel instead of typing your password.

## Keeping credentials safe

- Never paste your password into a notebook cell, a script, or a file inside the repository.
- Never commit `.netrc` or a copy of it. The repository's `.gitignore` excludes it, and the repository tests check for tokens.
- Saved outputs record the data URLs a lesson used, but never credentials or temporary signed links.
- If you think your password has been exposed, change it at [urs.earthdata.nasa.gov](https://urs.earthdata.nasa.gov/profile) and update `~/.netrc`.
