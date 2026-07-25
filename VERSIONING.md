# Versioning and stability policy

**Status:** Draft (pre-1.0). Process document; the version string it governs lives in the specification surfaces, not here.

This document states what a version number promises across each Provetrail surface, what counts as a breaking change, and what the `v0.1.0` freeze fixes. It expands `SPEC.md` Section 7; where the two differ, `SPEC.md` Section 7 is normative for the wire format and this document is normative for the process.

## What `v0.1.0` freezes

The freeze charter is authoritative in `SPEC.md` Section 7. In summary, tagging `v0.1.0` fixes as a stable contract: the leaf preimage and its domain-separation tag; the event envelope field set and the deterministic-CBOR encoding profile; the container, checkpoint, event-proof, and consistency schemas; the COSE protected-header profile (algorithm `-19`, the `application/vnd.provetrail.*` content types, key-id semantics); the registered failure-code meanings; and the published vector bytes. After the freeze, none of these changes except through a version increment that says so.

## One version, several surfaces

A single version string spans the surfaces that carry one, and `scripts/check_suite.py` fails the build if they disagree:

- **Specification** (`SPEC.md`, `CONFORMANCE.md`, `predicates/*.md`) - the normative version. `CITATION.cff` and both vector manifests (`suite_version`) and `registry.json` (`registry_version`) track it.
- **Conformance suite** - versioned in lockstep with the specification. The suite is the specification made executable; it does not carry an independent version line.
- **Predicate URI** - versioned separately in the path (`/v0.1`, `/v0.2`, `/v1`), governed by the URI policy below and in `predicates/run-provenance.md`.
- **Client packages** (`clients/` on crates.io, PyPI, npm) - versioned independently under semver as software. A client at `0.3.x` implementing specification `0.1.0` is normal: the client version tracks the library's own API and fixes, and its README states which specification version it verifies.

## What is a breaking change

A change is breaking if it does any of:

- changes the canonical bytes any conformant producer emits for an input it already handled;
- changes the verdict (accept/reject) or the registered failure code of an existing published vector;
- changes the meaning of a registered failure code, a media type, or the predicate statement.

A breaking change to the specification increments the major version and, before 1.0, may occur on a minor version only with an explicit migration note. A breaking change to the statement mints the next predicate URI path.

## What a minor version may do (the monotonic principle)

Before and after 1.0, a minor version **adds**; it never changes frozen bytes or existing verdicts. A minor version may: add new vectors (new ids, never mutations of existing ones); register new failure codes; add a new container kind under its own media type (for example the reserved redacted-record form); add OPTIONAL envelope or statement fields under the reservation rules of `SPEC.md` Section 7. A record valid under a given major version stays valid under every later minor version of it. New codes and vectors are additive demands on producers and verifiers, not redefinitions.

## Predicate URI policy

Per `predicates/run-provenance.md`: a versioned predicate path is immutable once its specification version freezes. A breaking change to the statement mints `/v0.2`; at specification 1.0 the URI becomes `/v1` and verifiers accept both during migration; after 1.0, minor versions never change the URI. Old paths stay resolvable forever.

## Deprecation

A registered code or a media type is never silently removed. To retire one, it is marked deprecated in `registry.json` and `SPEC.md` with the version it was deprecated in and the replacement; it keeps its meaning for records already produced. Deprecation is announced at least one minor version before any change of behavior that depends on it, and never removes the ability to verify a record produced under the earlier version.

## Where changes are recorded

Every normative change lands through the process in `GOVERNANCE.md` and is reflected in the version string that `scripts/check_suite.py` enforces. A release is cut per the procedure in `SPEC.md` Section 7 / the release documentation; the `v0.1.0` release is the one that mints the archival DOI.
