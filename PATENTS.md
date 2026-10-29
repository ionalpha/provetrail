# Patent non-assertion covenant

**Status:** In effect (pre-1.0).

## Why this document exists

Provetrail's prose specification is licensed under CC-BY-4.0 and its code, schemas, and vectors under Apache-2.0. Neither license fully settles patents for *independent implementations of the specification*: CC-BY-4.0 Section 2(b)(2) states that "Patent and trademark rights are not licensed under this Public License," and the Apache-2.0 patent grant runs with the licensed code, not with a clean-room implementation of the written standard. A standard people are asked to build on needs an explicit, credible patent posture. This document provides it.

Ion Alpha's IP posture for Provetrail is: no patents sought, name protected by trademark (and, as future work, a certification mark), and the standard kept freely implementable. This covenant makes that posture binding.

## The covenant

Ion Alpha irrevocably covenants not to assert any patent claim it owns or controls that would necessarily be infringed by implementing the required portions of the Provetrail specification (`SPEC.md`, `CONFORMANCE.md`, and the predicate definitions in `predicates/`) at the version this covenant ships with, against any party for making, using, selling, or distributing a conformant implementation of that specification.

This covenant:

- runs with the specification: it applies to every later version Ion Alpha publishes under this covenant, and, once granted for a version, is not withdrawn for that version;
- is non-exclusive and royalty-free, and requires no agreement, registration, or notice to rely on;
- covers implementations in any language, by any party, whether or not they use the Apache-2.0 reference code.

## What it does not cover

- **Trademark.** "Provetrail" is a trademark of Ion Alpha. This covenant grants no rights in the name or logo; use of the mark is governed separately (`README.md`, `NOTICE`).
- **Third-party patents.** Ion Alpha can only covenant over rights it owns or controls. The covenant is not a warranty that no third party holds a relevant patent. Provetrail deliberately assembles established, widely implemented primitives (deterministic CBOR, COSE, RFC 9162, Ed25519) precisely to minimize this exposure, but it is not a warranty.
- **Non-conformant use.** The covenant protects conformant implementations of the specification, not arbitrary unrelated products.

## Alternative considered

A heavier instrument, the Community Specification License 1.0 (as used by SPDX), carries built-in contributor patent commitments and is the natural choice if and when Provetrail moves to a multi-party foundation home. It is not adopted at v0.1: the single-editor covenant above is simpler, unilateral, and sufficient given the no-patents posture. Adopting the Community Specification License remains available as a future step (`GOVERNANCE.md`) and would not require re-licensing the existing text.
