# Operation API cases

These cases add one scalar `llm_defined` stage to the frozen arithmetic DAG.
Contract Review must compile the formula first. The Verifier then owns only the
coverage bins and predicates; the tool owns golden evaluation, solver stimulus,
canonical trace sampling, and witness validation.

Record for each attempt: formula, DAG predecessor, proposed bins, solver
witness status per bin, whether an operation extension bundle was incorrectly
created, and final deterministic verdict.
