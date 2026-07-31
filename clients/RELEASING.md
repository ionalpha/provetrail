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

Each package has its own workflow (`release-npm.yml`, `release-pypi.yml`,
`release-crate.yml`). On a push to `main` each one:

1. Runs `scripts/release_plan.py`, which compares the manifest version against what the
   registry already serves. If it is already published, the run stops here, in seconds.
2. Otherwise runs the **conformance gate**, the same reusable workflow
   (`conformance.yml`) every pull request has to pass. A red gate publishes nothing.
3. Publishes, and tags the commit (`npm-v0.2.0`, `py-v0.2.0`, `crate-v0.2.0`).

So an ordinary merge is silent, and a merge that bumps one manifest publishes exactly
that package. There is no path filter on the trigger, so a release missed because a
registry was unreachable self-heals on the next push. Publishing an existing version
fails at the registry by design, and the version check means a re-run never attempts
it, so a release cannot be overwritten.

The workflows create a git tag rather than a GitHub Release on purpose: Zenodo mints a
DOI from each Release, and the DOI belongs to the specification, not to a client
package bump.

### Why three workflows rather than one

A PyPI trusted publisher is bound to a specific workflow **filename**, matched against
the entry workflow. A reusable workflow cannot be a trusted publisher at all
(`pypi/warehouse#11096`), so the job that uploads to PyPI has to live in a top-level
file whose name PyPI already trusts. Renaming `release-pypi.yml`, or folding the upload
into a combined release workflow, invalidates the publisher and the upload is rejected.

The filename is therefore part of the release contract, not an implementation detail.
The three registries keep separate top-level workflows for that reason and share their
logic through `release-plan.yml` and `conformance.yml` instead of through a single entry
point. npm and crates.io have no such constraint, but they follow the same shape so
none of the three is a special case someone has to remember.

### Which number to bump

The clients implement the integrity tier, scoped in
[`conformance-scope.json`](./conformance-scope.json). Pre-1.0, a change that makes a
verifier **reject a record it previously accepted** is breaking (a consumer's
previously-passing input now fails), so it takes the minor bump (`0.1.x` → `0.2.0`),
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
  - Owner `ionalpha`, repository `provetrail`, workflow `release-pypi.yml`, environment
    `pypi`.
  - Create a GitHub *environment* named `pypi` in the repository settings.
  PEP 740 attestations are produced automatically on publish.
- **crates.io**: create an API token with publish scope and add it as the repository
  secret `CARGO_REGISTRY_TOKEN`. The workflow attaches a GitHub build-provenance
  attestation for the packaged `.crate`.

> **0.1.0 was not published this way.** All three packages went out within three minutes
> of each other on 2026-06-29, and neither the npm nor the PyPI release carries an
> attestation, which these workflows produce unconditionally. They were uploaded by
> hand. Treat the setup above as outstanding, not done: until it is complete, the
> promise at the top of this document is a promise about 0.2.0 onward.

## Verifying provenance (for anyone)

- **npm**: `npm audit signatures` after install, or the provenance panel on the
  package's npm page, shows the source commit and build.
- **PyPI**: the release's *attestations* are listed on the PyPI project page and served
  through the integrity API.
- **crates.io**: `gh attestation verify <path-to-.crate> --owner ionalpha` checks the
  build-provenance attestation against this repository.
