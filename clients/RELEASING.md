# Releasing the client packages

Each client package is published from GitHub Actions, never from a laptop, so every
release carries provenance: a signed attestation linking the published artifact to the
exact source commit and workflow run that produced it. This makes a genuine
`provetrail` package cryptographically distinguishable from a typosquat or a tampered
copy.

The packages version independently of the specification, and independently of each
other.

## To cut a release

Bump the version in the package manifest and merge it to `main`. That is the whole
procedure.

- npm: `clients/npm/package.json` (and `npm install --package-lock-only`)
- PyPI: `clients/python/pyproject.toml` and `src/provetrail/__init__.py`
- crates.io: `clients/rust/Cargo.toml` (and `cargo check` to refresh `Cargo.lock`)

`.github/workflows/release.yml` then, on that push:

1. Runs the **conformance gate** — the same reusable workflow (`conformance.yml`) that
   every pull request has to pass. A red gate publishes nothing.
2. Compares each manifest version against what the registry already serves.
3. Publishes only the packages whose version is not yet published, and tags the
   commit (`npm-v0.2.0`, `py-v0.2.0`, `crate-v0.2.0`).

So an ordinary merge that changes no version publishes nothing and is silent, and a
merge that bumps one manifest publishes exactly that one package. Publishing a version
that already exists fails at the registry by design, and the version check means a
re-run never attempts it, so a release cannot be overwritten.

The workflow creates a git tag rather than a GitHub Release on purpose: Zenodo mints a
DOI from each Release, and the DOI belongs to the specification, not to a client
package bump.

### Which number to bump

The clients implement the integrity tier, scoped in
[`conformance-scope.json`](./conformance-scope.json). Pre-1.0, a change that makes a
verifier **reject a record it previously accepted** is breaking — a consumer's
previously-passing input now fails — so it takes the minor bump (`0.1.x` → `0.2.0`),
not a patch.

## One-time setup (per registry)

These move publishing credentials off any personal machine and into the repository's
encrypted CI, so there are no long-lived tokens to paste or rotate by hand.

- **npm**: create an automation (or granular) access token scoped to publish
  `provetrail`, and add it as the repository secret `NPM_TOKEN`. The workflow requests
  `id-token: write`, so `npm publish --provenance` attaches a provenance attestation
  automatically.
- **PyPI**: configure a *trusted publisher* (OIDC, no token) at
  `https://pypi.org/manage/project/provetrail/settings/publishing/`:
  - Owner `ionalpha`, repository `provetrail`, workflow `release.yml`, environment
    `pypi`.
  - Create a GitHub *environment* named `pypi` in the repository settings.
  PEP 740 attestations are produced automatically on publish.
- **crates.io**: create an API token with publish scope and add it as the repository
  secret `CARGO_REGISTRY_TOKEN`. The workflow attaches a GitHub build-provenance
  attestation for the packaged `.crate`.

> If you configured the PyPI trusted publisher against the old `release-pypi.yml`, edit
> it to name `release.yml`. A trusted publisher is bound to a specific workflow
> filename, and publishing fails closed until it matches.

## Verifying provenance (for anyone)

- **npm**: `npm audit signatures` after install, or the provenance panel on the
  package's npm page, shows the source commit and build.
- **PyPI**: the release's *attestations* are listed on the PyPI project page and served
  through the integrity API.
- **crates.io**: `gh attestation verify <path-to-.crate> --owner ionalpha` checks the
  build-provenance attestation against this repository.
