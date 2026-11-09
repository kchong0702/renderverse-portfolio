from src.app.container import Container


def test_the_container_reads_the_agent_registry_once():
    container = Container()

    assert container.registry() is container.registry()
    assert set(container.registry()) == {a.name for a in container.settings().agents}


def test_workflow_graphs_keep_runs_in_the_containers_checkpointer():
    container = Container()

    graphs = [e.graph for e in container.executables() if e.kind == "workflow"]

    assert [graph.checkpointer for graph in graphs] == [container.checkpointer()] * 4
