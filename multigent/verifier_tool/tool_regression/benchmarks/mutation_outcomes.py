"""Recognize frozen C++ harness DUT failures, not arbitrary process failures."""

_COMMON = {
    10:"ghost valid during reset",20:"output changed while stalled",
    21:"unsolicited output",22:"mismatch index=",23:"accounting failure",
    24:"extra output after completion",
}
_PROFILE = {
    "scale":{11:"cannot accept reset-abort probe",12:"pre-reset output survived reset",
        13:"empty stage incorrectly depends on out_ready",14:"decoupled acceptance probe was lost",
        15:"decoupled probe changed while stalled",16:"decoupled probe duplicated"},
    "mask":{11:"cannot accept score reset probe",12:"pre-reset score survived reset",
        13:"cannot accept mask reset probe",14:"pre-reset mask survived reset",
        15:"skewed channel pairing failed",16:"stalled probe changed",17:"probe duplicated"},
}


def cpp_dut_failure(profile, result):
    """Exit codes 2/3, signals, missing vectors and unknown errors are not kills."""
    markers={**_COMMON,**_PROFILE[profile]}
    marker=markers.get(result.get("returncode"))
    return bool(result.get("compile_valid") and not result.get("passed") and marker
                and marker in result.get("log",""))
