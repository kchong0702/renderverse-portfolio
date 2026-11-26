import asyncio
from collections.abc import Callable, Mapping
from functools import partial
from typing import Any, override

import httpx
import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import Field

from src.app.container import Container
from src.shared.profile import Preferences
from tests.agents.career_consultant import test_career_consultant as career_consultant
from tests.agents.career_consultant.test_career_consultant import _loaded, _print
from tests.agents.career_director.test_career_director import _model
from tests.agents.productivity_assistant.test_productivity_assistant import ACME
from tests.conftest import ScriptedChatModel

BACKEND_TASK = "Name the Kubernetes work in the backend résumé's queue bullet"
LETTER_TASK = "Name the Kubernetes work in the cover letter's queue bullet"
TAILOR_TASK = "Tailor this résumé to job job-1, naming the Kubernetes work"
EMAIL_TASK = "Find what Acme emailed the user this week"
DONE = AIMessage("Both documents now name the Kubernetes work.")


class TaskModel(ScriptedChatModel):
    replies: list[AIMessage] = Field(default_factory=list)
    """Unused; scripts holds the replies"""

    scripts: dict[str, list[AIMessage]] = Field(default_factory=dict)
    """Each task's replies in turn, by the task's description"""

    crash: set[tuple[str, int]] = Field(default_factory=set)
    """The task's reply, by its index, that waits until cancelled the first time it
    is asked for, as if the process died there"""

    hang: set[str] = Field(default_factory=set)
    """The tasks whose first model call waits until it is cancelled"""

    log: list[str] = Field(default_factory=list)
    """What happened to the calls that crash or hang"""

    def _reply(self, messages: list[BaseMessage]) -> tuple[str, int]:
        """The task the messages are for and how many replies it already had"""
        task = next(m.text for m in messages if isinstance(m, HumanMessage))
        return task, sum(isinstance(m, AIMessage) for m in messages)

    @override
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Any = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """The task's next scripted reply"""
        self.requests.append(messages)
        task, index = self._reply(messages)
        return ChatResult(
            generations=[ChatGeneration(message=self.scripts[task][index])]
        )

    @override
    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: Any = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """The task's next scripted reply, after hanging or crashing as asked"""
        task, index = self._reply(messages)
        if task in self.hang:
            self.log.append(f"waiting {task}")
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.log.append(f"cancelled {task}")
                raise
        if (task, index) in self.crash and f"crashed {task}" not in self.log:
            self.log.append(f"crashed {task}")
            await asyncio.Event().wait()
        return self._generate(messages, stop, run_manager, **kwargs)


def _calls(*calls: tuple[str, str, dict[str, object]]) -> AIMessage:
    """One reply calling each (id, tool, args) at once"""
    return AIMessage(
        "",
        tool_calls=[{"id": id, "name": name, "args": args} for id, name, args in calls],
    )


def _assign(id: str, document_id: str, description: str):
    """A call (id, tool, args) giving career-consultant a task on the document"""
    return (
        id,
        "assign_career_consultant_task",
        {"document_id": document_id, "description": description},
    )


def _edits(prefix: str) -> list[AIMessage]:
    """career-consultant's replies for a task: read the document and the skill,
    propose, then report"""
    return [
        _calls((f"{prefix}-read", "read_document", {})),
        _calls(
            (
                f"{prefix}-skill",
                "read_file",
                {"file_path": "/modify-career-documents/SKILL.md"},
            )
        ),
        _calls(
            (
                f"{prefix}-propose",
                "propose_changeset",
                {
                    "changeset": career_consultant._changeset(
                        career_consultant.GOOD_EDIT
                    ).model_dump(mode="json")
                },
            )
        ),
        AIMessage(f"I proposed the {prefix} edit."),
    ]


def _container(
    director: ScriptedChatModel,
    consultant: ScriptedChatModel,
    assistant: ScriptedChatModel | None = None,
) -> Container:
    """A container whose agents run on the models, the subagents built first so the
    director's tasks run them"""
    container = Container()
    container.clients.artifact_service(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(partial(_print, sent=[])),
            base_url="http://artifact-service",
        )
    )
    container.career_consultant.agent(model=consultant)
    container.productivity_assistant.agent(model=assistant or TaskModel())
    container.career_director.agent(model=director)
    return container


def _director(
    director: ScriptedChatModel, consultant: ScriptedChatModel
) -> CompiledStateGraph:
    """career-director's agent on the models, with a checkpointer of its own"""
    return (
        _container(director, consultant)
        .career_director.agent()
        .copy(update={"checkpointer": InMemorySaver()})
    )


Answers = Mapping[str, Callable[[dict], object]]
"""ops-api's answer to each data request, by its tool"""

ANSWERS: Answers = {
    "read_document": lambda request: _loaded(
        title=f"Title of {request['document_id']}"
    ),
    "propose_changeset": lambda request: {
        "changeset_id": f"cs-{request['document_id']}"
    },
    "copy_for_job": lambda request: {
        "document_id": request["copy_id"],
        **_loaded(),
        "job": {
            "title": "Platform Engineer",
            "company": "Northwind Labs",
            "location": "Remote",
            "url": "https://jobs.example/northwind",
            "requirements": [],
        },
        "made": True,
        "rejected_changeset": False,
    },
    "threads": lambda request: {"threads": [ACME], "total": 1},
}

THREAD = {"configurable": {"thread_id": "t1"}}


async def _answer(
    graph: CompiledStateGraph, result: dict, asked: list[list[dict]]
) -> dict:
    """Answers every pause as ops-api does until the run ends, adding the requests of
    each pause to asked"""
    while pending := result.get("__interrupt__"):
        asked.append([p.value for p in pending])
        result = await graph.ainvoke(
            Command(
                resume={
                    p.id: ANSWERS[p.value["execute_tool"]](p.value) for p in pending
                }
            ),
            THREAD,
        )
    return result


async def _run(graph: CompiledStateGraph, asked: list[list[dict]]) -> dict:
    """Runs the director on a request, answering every pause"""
    return await _answer(
        graph,
        await graph.ainvoke(
            {
                "messages": [HumanMessage(career_consultant.REQUEST)],
                "profile_facts": career_consultant._state()["profile_facts"],
                "preferences": Preferences(),
            },
            THREAD,
        ),
        asked,
    )


def _answers_to(result: dict, call_id: str) -> list[ToolMessage]:
    """The tool messages answering the call"""
    return [
        m
        for m in result["messages"]
        if isinstance(m, ToolMessage) and m.tool_call_id == call_id
    ]


async def test_parallel_tasks_each_propose_and_a_second_task_on_one_document_is_refused():
    director = _model(
        _calls(
            _assign("backend", "doc-1", BACKEND_TASK),
            _assign("letter", "doc-2", LETTER_TASK),
            _assign("again", "doc-1", "Shorten the backend résumé's summary"),
        ),
        DONE,
    )
    consultant = TaskModel(
        scripts={BACKEND_TASK: _edits("backend"), LETTER_TASK: _edits("letter")}
    )
    asked: list[list[dict]] = []

    result = await _run(_director(director, consultant), asked)

    assert [
        sorted((r["execute_tool"], r["document_id"]) for r in pause) for pause in asked
    ] == [
        [("read_document", "doc-1"), ("read_document", "doc-2")],
        [("propose_changeset", "doc-1"), ("propose_changeset", "doc-2")],
    ]
    [backend] = _answers_to(result, "backend")
    [letter] = _answers_to(result, "letter")
    [again] = _answers_to(result, "again")
    assert (backend.status, backend.text) == ("success", "I proposed the backend edit.")
    assert (letter.status, letter.text) == ("success", "I proposed the letter edit.")
    assert backend.artifact == {"step_document_id": "doc-1"}
    assert letter.artifact == {"step_document_id": "doc-2"}
    assert again.status == "error"
    assert "already has a task in this reply" in again.text
    assert result["messages"][-1].text == DONE.text
    assert len(director.requests) == 2
    assert {
        "document",
        "desired_document_id",
        "actual_document_id",
        "changeset",
        "pdf_lines",
    }.isdisjoint(result)
    [first, *_] = consultant.requests
    assert [type(m) for m in first[1:]] == [HumanMessage]


async def test_a_task_past_its_step_limit_fails_alone_while_the_other_proposes():
    director = _model(
        _calls(
            _assign("backend", "doc-1", BACKEND_TASK),
            _assign("loop", "doc-2", LETTER_TASK),
        ),
        DONE,
    )
    consultant = TaskModel(
        scripts={
            BACKEND_TASK: _edits("backend"),
            LETTER_TASK: [
                _calls((f"facts-{i}", "read_profile_facts", {})) for i in range(60)
            ],
        }
    )
    asked: list[list[dict]] = []

    result = await _run(_director(director, consultant), asked)

    [backend] = _answers_to(result, "backend")
    [loop] = _answers_to(result, "loop")
    assert (backend.status, backend.text) == ("success", "I proposed the backend edit.")
    assert loop.status == "error"
    assert "stopped before finishing the task on document doc-2" in loop.text
    assert sum(r[1].text == LETTER_TASK for r in consultant.requests) < 40
    assert result["messages"][-1].text == DONE.text


async def test_a_task_starts_from_its_description_alone_and_works_on_its_document():
    director = _model(
        _calls(_assign("backend", "doc-1", BACKEND_TASK)),
        AIMessage("Done."),
    )
    consultant = TaskModel(scripts={BACKEND_TASK: _edits("backend")})
    asked: list[list[dict]] = []

    await _run(_director(director, consultant), asked)

    [system, task] = consultant.requests[0]
    assert task.text == BACKEND_TASK
    assert career_consultant.REQUEST not in system.text
    assert asked[0] == [{"execute_tool": "read_document", "document_id": "doc-1"}]


async def test_a_task_that_never_read_its_document_reports_the_one_it_was_given():
    director = _model(_calls(_assign("backend", "doc-1", BACKEND_TASK)), DONE)
    consultant = TaskModel(
        scripts={BACKEND_TASK: [AIMessage("Which bullet do you mean?")]}
    )

    result = await _run(_director(director, consultant), [])

    [backend] = _answers_to(result, "backend")
    assert (backend.text, backend.artifact) == (
        "Which bullet do you mean?",
        {"step_document_id": "doc-1"},
    )


async def test_a_tailoring_task_copies_its_document_and_proposes_on_the_copy():
    tailor = [
        _calls(("tailor-skill", "read_file", {"file_path": "/tailor-to-job/SKILL.md"})),
        _calls(("tailor-copy", "copy_for_job", {"job_id": "job-1"})),
        *_edits("tailor")[1:],
    ]
    director = _model(_calls(_assign("tailor", "doc-1", TAILOR_TASK)), DONE)
    consultant = TaskModel(scripts={TAILOR_TASK: tailor})
    asked: list[list[dict]] = []

    result = await _run(_director(director, consultant), asked)

    [[copy], [proposal]] = asked
    [task] = _answers_to(result, "tailor")
    assert (copy["execute_tool"], copy["document_id"], copy["job_id"]) == (
        "copy_for_job",
        "doc-1",
        "job-1",
    )
    assert (proposal["execute_tool"], proposal["document_id"]) == (
        "propose_changeset",
        copy["copy_id"],
    )
    assert task.artifact == {"step_document_id": copy["copy_id"]}


async def test_a_run_killed_with_one_task_done_resumes_without_repeating_any_request():
    tailor = [
        _calls(("tailor-skill", "read_file", {"file_path": "/tailor-to-job/SKILL.md"})),
        _calls(("tailor-copy", "copy_for_job", {"job_id": "job-1"})),
        *_edits("tailor")[1:],
    ]
    director = _model(
        _calls(
            _assign("backend", "doc-1", BACKEND_TASK),
            _assign("tailor", "doc-2", TAILOR_TASK),
        ),
        DONE,
    )
    consultant = TaskModel(
        scripts={BACKEND_TASK: _edits("backend"), TAILOR_TASK: tailor},
        crash={(TAILOR_TASK, 4)},
    )
    graph = _director(director, consultant)
    asked: list[list[dict]] = []

    run = asyncio.create_task(_run(graph, asked))
    while not consultant.log or not any(
        task.result for task in (await graph.aget_state(THREAD)).tasks
    ):
        await asyncio.sleep(0.01)
    run.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run
    before = len(consultant.requests)
    result = await _answer(graph, await graph.ainvoke(None, THREAD), asked)

    requests = [(r["execute_tool"], r["document_id"]) for pause in asked for r in pause]
    [copy_id] = [r["copy_id"] for pause in asked for r in pause if "copy_id" in r]
    assert sorted(requests) == sorted(
        [
            ("read_document", "doc-1"),
            ("copy_for_job", "doc-2"),
            ("propose_changeset", "doc-1"),
            ("propose_changeset", copy_id),
        ]
    )
    assert consultant.log == [f"crashed {TAILOR_TASK}"]
    [resumed] = consultant.requests[before:]
    assert (resumed[1].text, len(resumed)) == (TAILOR_TASK, 10)
    assert [m.text for m in _answers_to(result, "backend")] == [
        "I proposed the backend edit."
    ]
    assert [m.text for m in _answers_to(result, "tailor")] == [
        "I proposed the tailor edit."
    ]
    assert result["messages"][-1].text == DONE.text


async def test_an_email_task_pauses_for_its_data_request_and_returns_the_reply():
    director = _model(
        _calls(
            (
                "email",
                "assign_productivity_assistant_task",
                {"description": EMAIL_TASK},
            )
        ),
        AIMessage("Priya from Acme wrote about your interview."),
    )
    assistant = TaskModel(
        scripts={
            EMAIL_TASK: [
                _calls(("search", "search_threads", {"sender": "acme.com"})),
                AIMessage("Priya from Acme wrote about the interview."),
            ]
        }
    )
    graph = (
        _container(director, career_consultant._model(), assistant)
        .career_director.agent()
        .copy(update={"checkpointer": InMemorySaver()})
    )
    asked: list[list[dict]] = []

    result = await _run(graph, asked)

    assert [[r["execute_tool"] for r in pause] for pause in asked] == [["threads"]]
    [email] = _answers_to(result, "email")
    assert email.text == "Priya from Acme wrote about the interview."
    assert email.artifact == {"step_detail": "email"}
    assert [m.text for m in assistant.requests[0][1:]] == [EMAIL_TASK]
    assert result["messages"][-1].text == "Priya from Acme wrote about your interview."
