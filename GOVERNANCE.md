# Governance

**Status:** Process document (pre-1.0).

How Provetrail changes, who maintains it, and the rule that keeps the specification and its executable conformance suite from drifting apart. This document is process; `SPEC.md` and `CONFORMANCE.md` are the normative content. Settled decisions that are not specification text are recorded in [`DECISIONS.md`](./DECISIONS.md).

## Maintainership

Provetrail is edited by **Ion Alpha**, as a vendor-neutral, implementation-neutral standard. The standard is deliberately not bound to any single implementation; any conformant producer or verifier in any language is a first-class citizen (`CONTRIBUTING.md`).

This is a single-editor model at v0.1 by intent, not by principle. The design goal is a standard other parties can adopt and, in time, co-steward. The door is open to a future multi-party home (a working group or foundation) once there is adoption to justify it; the licensing and patent posture (`PATENTS.md`) is chosen to make that transition possible without re-licensing.

## How a normative change lands

A change to the wire format, a check, a failure code, or the statement follows one path:

1. **Issue.** Open an issue describing the problem or gap, using the relevant template.
2. **Pull request.** Open a pull request against the affected document (`SPEC.md`, `CONFORMANCE.md`, `predicates/`, `cddl/`), referencing the issue.
3. **Accompanying vector.** A normative change that adds or changes a check, or a failure code, ships with the conformance vector that exercises it. A rule with no vector is not enforceable and does not land: the suite operationally defines the standard, so the vector is the change. A vector is added by the reference generator and published here (`CONFORMANCE.md` Section 7); it is never hand-authored.
4. **Version bump.** The change carries the version increment `VERSIONING.md` requires (breaking vs additive), applied to every surface at once; `scripts/check_suite.py` refuses a partial bump.

The conformance gate (`.github/workflows/conformance.yml`) is the single required check for the protected branch, so no normative change merges without passing exactly what a release must pass.

## Registry change policy

The failure-code registry (`registry.json`, prose companion `CONFORMANCE.md` Section 6) is a published artifact and changes under a fixed discipline, mirrored in the predicate design:

- **Layer-prefixed.** Every code is dotted and names its layer (`enc.`, `chain.`, `sign.`, `record.`, `merkle.`, `gov.`, `shallow.`).
- **Single defect per code.** A code names exactly one rejection reason. A rejection emits the registered code, never a free-form string; two distinct defects never share a code.
- **At least one vector.** A code with `pinned` status names the vectors that pin it, and `scripts/check_suite.py` enforces that the list matches the manifests exactly. The only codes without a vector are those with `deferred`, `operational`, or `producer` status, each of which is registered for a stated reason (`CONFORMANCE.md` Section 6).
- **Adding a code is a versioned change.** New codes are additive (`VERSIONING.md`); a code's meaning, once registered and frozen, does not change.

The predicate URI follows the same immutability discipline in its own path space (`predicates/run-provenance.md`, `VERSIONING.md`).

## Conformance claims

Conformance is self-declared, in the exact form given in `CONFORMANCE.md` Section 8. A claim names an L-tier and a suite version and nothing else. "Provetrail" is a trademark of Ion Alpha; a conformance claim describes an implementation's behavior against the published suite and is not a certification by Ion Alpha. A certification-mark program, under which an independent steward would certify implementations against the suite, is future work and does not exist at this version.

## Security

Security defects follow the private-disclosure process in `SECURITY.md`. A fix that closes a soundness defect ships with the vector that would have caught it, per the change process above.
