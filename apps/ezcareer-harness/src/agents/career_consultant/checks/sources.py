from src.agents.career_consultant import CareerConsultantState


def sources(state: CareerConsultantState) -> dict[str, str]:
    """The text of every PDF line and fact an edit may cite, by citation"""
    return {line.id: line.text for line in state["lines"]} | {
        f"fact:{fact.id}": fact.text for fact in state["facts"]
    }
