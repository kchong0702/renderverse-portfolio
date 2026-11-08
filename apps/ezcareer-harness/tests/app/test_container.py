from src.app.container import Container


def test_the_container_reads_the_registered_agents_once():
    container = Container()

    assert container.agents() is container.agents()
    assert set(container.agents()) == {a.name for a in container.settings().agents}
