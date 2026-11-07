from src.features.analyse_job.graph import AnalyseJobOutput, build_graph


async def analyse_posting(task: object) -> AnalyseJobOutput:
    """Analyse one posting for one profile with the current settings"""
    return AnalyseJobOutput.model_validate(await build_graph().ainvoke(task))
