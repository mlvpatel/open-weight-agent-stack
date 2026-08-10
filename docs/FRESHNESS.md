# The freshness watcher

Model licences change. Parameter counts get corrected. A model announced with benchmark figures turns out to have no downloadable weights. This manual's central claim is that its facts hold up when checked, and that claim decays unless something checks them after publication.

`scripts/watch_upstream.py` runs weekly and reports drift in the facts the manual publishes.

## What it watches

**Model metadata.** For each of the 24 models the manual makes claims about, it reads the Hugging Face API and keeps only the fields the manual actually asserts: licence tag, licence name, gated status, and whether the model still resolves at all. Everything else about a model card changes constantly and would produce noise.

**Build dependencies.** The pinned versions in `package.json` against what npm currently publishes. This is the same machine pointed at a different source, not a second bot.

## Why it does not act on what it sees once

Upstream metadata flaps. A card gets edited and reverted within the hour. An API returns a partial record mid-deploy. A single observation is not evidence.

A change must be observed on **two consecutive runs** before it is reported. The count lives in `.github/upstream-state.json`, pushed to a dedicated `freshness-state` branch after **every** run. That branch exists because the counter has to be written on runs where nothing was found, which is exactly when there is no pull request to carry it, and because `main` is protected.

While a change is unconfirmed the stored baseline deliberately does **not** advance. If it did, the next run would compare the new value against itself, find no difference, and the counter would freeze below the threshold forever. That bug shipped once and is now pinned by `scripts/test_watch_upstream.py`, which asserts that a stable change is reported and a flapping one never is.

## Why it does not edit the manual

The watcher reports; it never writes to `MANUAL.md`. A detection bug can then produce a noisy pull request, which costs you a moment's reading. If it could edit, the same bug could silently rewrite published facts, which is the failure this whole milestone exists to prevent.

Each finding carries a link to the primary source. Verify against it before merging: a licence claim is legal guidance by implication.

## Why it needs a GitHub App

Pull requests created with the default `GITHUB_TOKEN` **receive no check runs**. GitHub suppresses them deliberately, to stop workflows triggering themselves recursively.

With required status checks enabled, a pull request with no checks can never satisfy them. The bot's pull requests would sit unmergeable forever. A GitHub App token is issued to a distinct identity, so its pull requests run the full suite like any other.

### Setup

1. **Settings → Developer settings → GitHub Apps → New GitHub App**
2. Permissions: **Contents: Read and write**, **Pull requests: Read and write**
3. Install it on this repository
4. Generate a private key
5. Add repository secrets `APP_ID` and `APP_PRIVATE_KEY`
6. Add a repository variable `FRESHNESS_APP_ENABLED` set to `true`

Until step 6, the watcher still runs and still reports. It writes its findings to the workflow log with a warning instead of opening a pull request, so nothing is lost while the App is unconfigured.

## One operational caveat

GitHub disables scheduled workflows in public repositories after **60 days without repository activity**. Any commit resets that clock, and the watcher's own pull requests count as activity, so an actively maintained repository is not at risk. A repository left completely untouched for two months is, and the failure is silent: the schedule simply stops.

If this repository goes quiet for that long, re-enable the workflow from the Actions tab. There is no way to detect the condition from inside a workflow that is no longer running.

## Running it by hand

```bash
python3 scripts/watch_upstream.py
```

Exit codes: `0` no confirmed drift, `2` drift found and written to `drift-report.md`, anything else is a failure.
