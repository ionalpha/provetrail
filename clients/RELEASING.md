# Releasing the client packages

Each client package is published from GitHub Actions, never from a laptop, so every
release carries provenance: a signed attestation linking the published artifact to the
exact source commit and workflow run that produced it. This makes a genuine
`provetrail` package cryptographically distinguishable from a typosquat or a tampered
copy.

The packages version independently of the specification, so each has its own manual
release workflow under `.github/workflows/`.

## To cut a release

1. Bump the version in the package manifest and commit it:
   - npm: `clients/npm/package.json`
   - PyPI: `clients/python/pyproject.toml`
   - crates.io: `clients/rust/Cargo.toml`
2. Run the matching workflow from the Actions tab (`Release npm package`,
   `Release PyPI package`, or `Release crate`).

The workflow runs the tests, builds, attests, and publishes. Publishing a version that
already exists fails by design, so a re-run cannot overwrite a release.

## One-time setup (per registry)

These move publishing credentials off any personal machine and into the repository's
encrypted CI, so there are no long-lived tokens to paste or rotate by hand.

- **npm**: create an automation (or granular) access token scoped to publish
  `provetrail`, and add it as the repository secret `NPM_TOKEN`. The workflow requests
  `id-token: write`, so `npm publish --provenance` attaches a provenance attestation
  automatically.
- **PyPI**: configure a *trusted publisher* (OIDC, no token) at
  `https://pypi.org/manage/project/provetrail/settings/publishing/`:
  - Owner `ionalpha`, repository `provetrail`, workflow `release-pypi.yml`,
    environment `pypi`.
  - Create a GitHub *environment* named `pypi` in the repository settings.
  PEP 740 attestations are produced automatically on publish.
- **crates.io**: create an API token with publish scope and add it as the repository
  secret `CARGO_REGISTRY_TOKEN`. The workflow attaches a GitHub build-provenance
  attestation for the packaged `.crate`.

## Verifying provenance (for anyone)

- **npm**: `npm audit signatures` after install, or the provenance panel on the
  package's npm page, shows the source commit and build.
- **PyPI**: the release's *attestations* are listed on the PyPI project page and served
  through the integrity API.
- **crates.io**: `gh attestation verify <path-to-.crate> --owner ionalpha` checks the
  build-provenance attestation against this repository.
