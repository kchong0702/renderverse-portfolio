from src.app.container import Container


def test_the_container_reads_the_agent_registry_once():
    container = Container()

    assert container.registry() is container.registry()
    assert set(container.registry()) == {a.name for a in container.settings().agents}
