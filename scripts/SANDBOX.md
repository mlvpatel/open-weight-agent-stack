# Why the Chromium sandbox is disabled during rendering

`scripts/puppeteer.json` passes `--no-sandbox` and `--disable-setuid-sandbox` to the
Chromium instance that Mermaid uses to rasterise diagrams.

This is required because the renderer runs inside a GitHub Actions container, where the
kernel user-namespace cloning that Chromium's sandbox depends on is unavailable. Without
these flags the process fails to launch.

The risk this accepts, and why it is acceptable here:

- The only input Chromium ever loads is a Mermaid diagram source file taken from
  `MANUAL.md` inside this repository. It never loads a remote URL, and it never loads
  content supplied by a pull request from a fork, because rendering runs only on
  repository-controlled sources.
- The browser process has no network access requirement and no credentials in its
  environment.
- A malicious diagram would need a Chromium sandbox-escape chain to affect anything, and
  the blast radius would be an ephemeral CI runner with a read-only checkout.

If diagram sources ever become externally contributed and rendered before review, this
trade stops being acceptable and rendering must move to a sandboxed runner.
