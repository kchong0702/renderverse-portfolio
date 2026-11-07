from langchain_core.runnables import RunnableLambda

from src.app.a2a.flow import Flow
from src.features.import_document import ImportInput, import_task

FLOWS: list[Flow] = [
    Flow(
        name="import-resume",
        description="Turns an uploaded résumé (PDF or Word, base64 in `file`) into "
        "a draft document whose values cite the file's lines, printed to PDF",
        input_schema=ImportInput,
        graph=RunnableLambda(import_task),
    ),
]
"""Every flow the server runs; add a feature's Flow here to serve it"""
