from src.agents.career_consultant import CareerConsultantState


def sources(state: CareerConsultantState) -> set[str]:
    """Every PDF line id and fact:<id> an edit may cite"""
    return {line.id for line in state["lines"]} | {
        f"fact:{fact.id}" for fact in state["facts"]
    }
