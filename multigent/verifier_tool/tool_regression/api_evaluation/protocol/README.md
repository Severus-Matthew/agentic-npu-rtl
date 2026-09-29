# Protocol API cases

These cases target the existing `y` ready/valid channel but request temporal or
classification behavior absent from the protocol pool. Existing handshake and
stall-stability features remain active. The Verifier must bind real `valid`,
`ready`, and (when requested) `payload` signals, reuse resolved helpers, and
implement only the residual assertion/coverage/stimulus behavior.

Record for each attempt: requested bound, reused feature IDs/helpers, concrete
signal bindings, generated entry-point symbols, reachability result, and final
deterministic verdict.
