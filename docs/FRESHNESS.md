# The freshness watcher

Model licences change. Parameter counts get corrected. A model announced with benchmark figures turns out to have no downloadable weights. This manual's central claim is that its facts hold up when checked, and that claim decays unless something checks them after publication.

`scripts/watch_upstream.py` runs weekly and reports drift in the facts the manual publishes.

## What it watches

**Exact Hugging Face checkpoints.** The auditable contract in
[`.github/freshness-sources.json`](../.github/freshness-sources.json) lists the exact checkpoint
links declared in MANUAL.md section 27.1 and `docs/MODELS.md`. The watcher reads the Hugging Face
API for each **automated** entry and compares only availability, licence tag, licence name, and
gated status. A new exact model-card link makes `python3 scripts/test_watch_upstream.py` fail
until it is added to `automated_models` or to `manual_only` with a narrow reason. Organisation
pages, vendor licence files, parameter counts, benchmark numbers, prices, and non-Hugging-Face
sources are not metadata-monitored; re-verify those facts against their linked primary source.
The committed state retains prior verified metadata only for checkpoints already observed. Newly
added checkpoints, including the corrected Devstral identifier, establish a baseline on their first
successful API response rather than receiving invented values in the repository.

**Build dependencies.** The pinned versions in `package.json` against what npm currently publishes. This is the same machine pointed at a different source, not a second bot.

## Why it does not act on what it sees once

Upstream metadata flaps. A card gets edited and reverted within the hour. An API returns a partial record mid-deploy. A single observation is not evidence.

A change needs a stable baseline and then must be observed on **two consecutive runs** before it is
reported: three observations in the normal baseline/change/change sequence. The count lives in
`.github/upstream-state.json`, pushed to a dedicated `freshness-state` branch after **every** run.
That branch exists because the counter has to be written on runs where nothing was found, which is
exactly when there is no pull request to carry it, and because `main` is protected.

While a change is unconfirmed the stored baseline deliberately does **not** advance. If it did, the
next run would compare the new value against itself, find no difference, and the counter would
freeze below the threshold forever. A 404 or 410 is the only HTTP result that means a card is
absent, and it follows the same debounce. Timeouts, DNS/connection errors, 401/403, 429, 5xx,
invalid JSON, and other transport failures are **indeterminate**: they do not overwrite a usable
baseline, increment pending drift, or claim that a model disappeared. The run logs a warning and
resumes the existing debounce when a usable observation returns. These cases are pinned by
`scripts/test_watch_upstream.py`.

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

Until step 6, the watcher still runs and still reports. It writes its findings to the workflow log
and job summary with a warning instead of opening a pull request, so nothing is lost while the App
is unconfigured. The normal `GITHUB_TOKEN` is used only to persist the observation-state branch;
the checkout disables persisted credentials. The App token is minted only after confirmed drift and
is used only for `create-pull-request`.

## One operational caveat

GitHub disables scheduled workflows in public repositories after **60 days without repository activity**. Any commit resets that clock, and the watcher's own pull requests count as activity, so an actively maintained repository is not at risk. A repository left completely untouched for two months is, and the failure is silent: the schedule simply stops.

If this repository goes quiet for that long, re-enable the workflow from the Actions tab. There is no way to detect the condition from inside a workflow that is no longer running.

## Running it by hand

```bash
python3 scripts/watch_upstream.py
```

Exit codes: `0` means no confirmed drift (including indeterminate-source warnings), `2` means
confirmed drift was written to `drift-report.md`, and `1` means a local coverage-contract or
configuration failure. A manual run is useful for inspection, but it cannot prove a live source is
current unless the API and every linked non-API primary source are reachable and reviewed.
