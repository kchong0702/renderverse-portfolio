from src.agents.career_consultant.page_fit import PageCountPreservationConfig
from src.agents.registry import AgentProfile


class CareerConsultantProfile(AgentProfile):
    page_count_preservation: PageCountPreservationConfig = PageCountPreservationConfig()
    """How propose_changeset keeps a document's page count"""
