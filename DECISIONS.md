# Decision records

Settled decisions that shape the standard but do not belong in the specification text. Each record is dated, states the decision, and records the evidence it rests on, so a closed question is not re-opened without new facts. Process context is in `GOVERNANCE.md`.

## D1 (2026-07-31): the name is Provetrail, and it is frozen

**Decision.** The standard keeps the name Provetrail. The rename question, raised against the phonetic neighbor "ProofTrail" (prooftrails.com), was assessed on 2026-07-31 and is settled.

**The name is a hashed constant, not a label.** The name lives inside the signed bytes: the leaf domain separator `provetrail/event/v1\n` is part of every leaf hash preimage, and the COSE protected header carries the content type `application/vnd.provetrail.checkpoint+cbor`. The freeze charter enumerates both among the constants frozen at v0.1.0. A rename would therefore regenerate all 65 published conformance vectors, republish three client packages under a new registry name, and invalidate every record already signed. The window in which renaming was free closed when the first artifacts were published on 2026-06-29; since then it has been a wire-format change, the most expensive kind of change this standard defines.

**No conflict exists.** prooftrails.com is a waitlist-stage consumer career product ("Daily Proof of progress for builders and job seekers": GitHub/X/LeetCode integrations, IPFS content IDs, recruiter discovery). It differs from this standard in word (Proof vs Prove), market, technology, and channel, and it makes no claim near verifiable execution provenance. No USPTO registration for ProofTrail or Proof Trail was found in classes 9 or 42, and the phrase is already diluted across unrelated parties (prooftrail.net, prooftrail.co.uk, proofrail.dev), so no party holds it distinctively.

**Residual cost and mitigation.** Phonetic proximity makes plain search noisier. That is a discovery cost, paid by keeping `provetrail.org` canonical everywhere and letting the technical context disambiguate, not by renaming.

**Out of scope.** A trademark filing is a separate, post-publish commercial decision and does not gate the freeze. No outreach to prooftrails.com is warranted.
