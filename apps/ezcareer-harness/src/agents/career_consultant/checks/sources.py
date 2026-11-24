from src.agents.career_consultant import CareerConsultantState


def sources(state: CareerConsultantState) -> set[str]:
    """Every source an edit may cite: the id of each line of the uploaded résumé file
    and fact:<id> of each profile fact"""
    return {pdf_line.id for pdf_line in state.get("pdf_lines", [])} | {
        f"fact:{profile_fact.id}" for profile_fact in state["profile_facts"]
    }
