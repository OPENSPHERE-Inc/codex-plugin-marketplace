# Divergence prevention

Divergence occurs when fixing one finding produces the next and findings continue through repeated fixes. The producer avoids these patterns when creating or revising a design; the reviewer detects them during design review.

## Divergence patterns

- Undecided specification or invariant: the design leaves input ranges, ordering/exclusion guarantees, ownership and lifetime, error behavior, or other implementation dependencies undecided. This includes listing options without choosing one or deferring a decision to implementation.
- Unclosable problem class: the approach's correctness depends on enumerating individual cases over an unbounded range. Addressing one counterexample leaves unlimited counterexamples of the same class (such as an architecturally unavoidable race window or regex parsing of unconstrained input).
- Unadjudicated conflict: the design does not prioritize conflicting requirements or quality goals.
- Mismatch with the existing design: the approach conflicts with existing ownership, threading, error handling, or other design conventions without a reconciliation policy.

## producer

- Undecided specification or invariant: decide it in the design. If the task and existing code cannot settle it, explicitly label the adopted assumption as an assumption.
- Unclosable problem class: choose an approach that closes the class structurally, such as a grammar-based parser or serialization onto one owner. If unavailable, state the accepted scope (input constraints, preconditions, tolerated residual risk) and declare everything outside it out of scope.
- Unadjudicated conflict: state which side takes priority and why.
- Mismatch with the existing design: follow the existing design. For a deviation, state the reason and how to reconcile the boundary.

## reviewer

- Raise each pattern match as Major or higher, choosing the fix direction from the producer section.
- For an unclosable problem class, do not request fixes for individual counterexamples. Cite them only as evidence that the class exists.
- When the design states its accepted scope, do not raise counterexamples outside it. Challenge the scope itself only if the task cannot be met within it.
