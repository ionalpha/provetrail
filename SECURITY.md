# Security policy

Provetrail is a standard for producing evidence other parties rely on, so a defect in the specification, the conformance suite, or a client verifier can cause a party to trust a record it should have rejected. We take reports of such defects seriously.

## Reporting a vulnerability

Report suspected vulnerabilities privately to **contact@ionalpha.io**. Please do not open a public issue for a security defect until it has been triaged and a fix or mitigation is available.

A useful report names the surface (below), the version or commit, and a concrete failure: for a verifier, the record or vector that is accepted-but-should-be-rejected (or the reverse) and why; for the specification, the text that permits an unsound record; for the vectors, the vector whose bytes or expected verdict is wrong.

We aim to acknowledge a report within five working days and to agree a disclosure timeline with the reporter. Coordinated disclosure is preferred: we will credit reporters who want credit.

## Scope

This repository is several surfaces with different failure modes. All are in scope:

- **Specification (`SPEC.md`, `CONFORMANCE.md`, `predicates/`).** A soundness defect: text that lets an invalid record verify, a canonicalization rule that admits two encodings of one value, an underspecified check a conformant verifier could skip.
- **Client verifiers (`clients/`).** A verifier that reaches the wrong verdict on a record: accepting a tampered record, rejecting a valid one, or emitting the wrong failure code. Divergence between the clients and the reference implementation on published vectors is a defect.
- **Conformance vectors (`vectors/`).** A vector whose bytes do not match its description, whose expected verdict is wrong, or a missing vector that lets an important defect go untested. Because the suite operationally defines the standard, a wrong vector propagates into every conformant verifier.
- **Site and published artifacts.** The `provetrail.org` site, the `w3id.org` predicate identifier, and the published packages (crate / PyPI / npm). A stale or wrong published artifact that misrepresents the standard is in scope.

## Not a vulnerability

- **The test signing key.** The `crypto/` conformance vectors are signed under a fixed Ed25519 key published in `vectors/crypto/manifest.json`. It is deliberately public and is not for production. Signing anything real with it, or "recovering" it, is expected, not a finding.
- **Pre-freeze format change.** Until `v0.1.0` is tagged the on-the-wire format is a working draft (`SPEC.md` Section 7). A record produced against a pre-freeze draft failing under a later draft is expected behavior, not a vulnerability.
- **Relying on a draft in production.** The specification states it MUST NOT be relied on as a production security control before the freeze. Doing so anyway is a deployment choice, not a defect in the standard.

## Handling

Fixes to a soundness defect land through the normal change process (`GOVERNANCE.md`): a specification or vector change that closes a defect ships with the vector that would have caught it, so the suite grows to cover it. Where a fix changes canonical bytes or the verdict of an existing vector, it is a breaking change under `VERSIONING.md` and is versioned accordingly.
