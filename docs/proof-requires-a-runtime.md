# Proof requires a runtime

### Why a signed log isn't proof of what your agent did

Every team shipping agents is converging on the same question: *how do you know what the agent actually did?* Not what it said it did in a summary, what actually executed, against real systems, on someone's behalf. The common answer is a **signed record**: the agent, or a wrapper around it, emits a receipt, signs it with Ed25519, canonicalizes it deterministically, anchors identity with did:web, and hands you a verifiable artifact. Verify the signature, trust the contents.

That is a good and necessary primitive. It is also not proof. It is **attestation**, and the difference is the whole game.

## Attestation vs proof

An attestation is **a signature over a claim the signer could have fabricated.** If the same component that performs the work also writes the record of the work, a valid signature tells you only that *this signer asserts this happened*, not that it happened. A wrapper that signs "I summarized the document" signs that string whether or not it summarized anything. The cryptography is sound; it is securing the wrong thing. You have proven authorship of a claim, not the truth of it.

Proof is **a record emitted by a substrate that could not have done otherwise.** If the component that *enforces* execution, admits the action, scopes the capability, gates on budget and approval, contains the side effects, is also what emits the record, then the record is not a claim about the work. It is a byproduct of the enforcement. The agent cannot record "I only touched the staging database" while touching production, because the substrate that mediated the call is what wrote the line, and it mediated the real call. The honesty is structural, not asserted.

This is why the most rigorous attempts in this space reach for hardware, a trusted execution environment: without a trusted substrate, a software record is only as honest as whatever produced it, so they push the trust boundary down to silicon. That instinct is exactly right, *the record is only as strong as the thing that emits it*. But a TEE proves the integrity of the execution environment; on its own it does not prove the work was governed, scoped, or correct, and it taxes every deployment with an enclave. The cheaper and more general answer is a **governed runtime**: enforce the invariants in software at the point where actions are dispatched, and emit the record from there.

## But then you're just trusting the runtime

Yes. And that is the point, not a hole in it.

The record is only as strong as the thing that emits it, so a governed runtime asks you to trust the runtime. But trust never disappears in these systems; it only ever *moves*. The alternative to trusting the runtime is trusting an unbounded, opaque, nondeterministic agent and model to honestly report on themselves. A governed runtime relocates that trust to a far better anchor:

- It is **one small, fixed component**, not an open-ended generative process. You can read all of it.
- It is **open and reproducible**: given the same inputs its behavior replays deterministically, so its records can be re-derived rather than taken on faith.
- Its records are **tamper-evident and independently verifiable**, and the outcome checks it commits can be **re-run** by anyone with access to the system it touched.

So a compromised or dishonest runtime is *detectable* in a way a self-reporting agent never is. You have traded trust in an unauditable many for trust in an auditable one. That trade is the entire value.

## What a record should commit to

A receipt worth trusting commits, at minimum, to facts the *emitter* controlled and the agent could not forge:

1. **Admission before execution** - the action was checked against policy *before* it ran, and the decision is in the record.
2. **Capability honored** - the action stayed within the capabilities it was granted; out-of-scope calls were refused, and the refusal is recorded.
3. **Budget and approval** - resource ceilings and human-approval gates fired where required, recorded as enforced facts, not narrated intentions.
4. **Outcome against reality** - where a claim can be checked against real system state, the check and its evidence are committed (a hash of what was observed), so an authorized party can re-run it without trusting the producer.
5. **Tamper-evidence** - the records are chained so a later edit is detectable, and signed so the emitter is provable.

Note what carries the weight. Items 1 to 3 are only meaningful if a runtime actually *enforces* them. A format can describe them; only a substrate can guarantee them. That is the line between a schema and a proof.

## A conformance suite that respects the difference

Interop needs shared, checkable levels, and they should be honest about what each one buys. Provetrail's conformance tiers are defined so that a verifier passes a tier only by accepting every valid vector and rejecting every tampered one with the correct failure code:

- **L1 Structural** - the record is canonically encoded and correctly ordered. Well-formed, no cryptography yet.
- **L2 Cryptographic** - the signature verifies under the named key, and every event is committed under the signed root. This is the "signed" rung, and a wrapper can reach it.
- **L3 Transparency** - inclusion and consistency proofs hold against a signed root, so the history cannot be rewritten after the fact.
- **L4 Governance and ground truth** - every side-effecting action has a matching admission record, recorded gate results are consistent with what executed, and every success claim is bound to an independent check. **This rung is unreachable by a wrapper, a logger, or a post-hoc converter.** It requires the work to run inside a substrate that mediated and recorded every action, and it requires "success" to mean a check passed, not that the agent said so.

The top rung is the point. A signed receipt and a verifier's opinion get you to the middle of this ladder; the difference between *signed* and *enforced*, and between *claimed* and *checked against reality*, lives at L4. A buyer who cannot yet tell those apart will be sold the cheaper one as if it were the dearer.

## Why we are saying this

Provetrail is an open, vendor-neutral standard; any conformant producer or verifier in any language is a first-class citizen. We also build a governed agent runtime, which is why we care about this line: that runtime enforces these invariants at the dispatch boundary because it has to mediate the action anyway, so emitting the proof is nearly free, and uniquely trustworthy, precisely because the thing that wrote the record is the thing that refused the bad path. We would rather the whole field adopt the shared primitives, Ed25519, deterministic CBOR, transparency logs, did:web, and then compete honestly on the rung that matters: whether your proof was *enforced* or merely *signed*.

The standard we want to exist is one where the question "is this attestation or proof?" has a machine-checkable answer. Until it does, the market will reward verifiability theater: shallow records that look like proof to anyone who cannot evaluate the depth. The fix is not more signatures. It is a runtime under the record.

---

*The Provetrail specification, conformance suite, and reference verifiers (one in Go, plus independent verifiers in Rust, Python, and JavaScript) are at [github.com/ionalpha/provetrail](https://github.com/ionalpha/provetrail).*
