"""Compatibility import; orchestration.graph owns every executable route."""
from multigent.orchestration.graph import build_workflow_graph, main
if __name__ == '__main__':
    main()
