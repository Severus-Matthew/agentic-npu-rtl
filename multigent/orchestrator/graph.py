"""LangGraph workflow definition.

Target flow:
START -> architect -> {rtl_generator || verifier} -> verification_tools
FAIL -> debugger -> rtl_generator -> verification_tools
PASS -> synthesis_tools -> ppa_judge
OPTIMIZE -> rtl_generator -> verification_tools
ACCEPT -> finalization -> END
"""
