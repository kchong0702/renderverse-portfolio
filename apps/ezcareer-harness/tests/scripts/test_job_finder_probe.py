import respx

from scripts import probe

URL = "https://jobs.example.com/gone"


@respx.mock
async def test_probe_reports_why_an_analysis_failed():
    respx.get(URL).respond(404)

    result = await probe.probe(
        probe.WORKFLOWS["analyse-job"], {"url": URL, "profile": {"facts": []}}
    )

    assert result["output"] is None
    assert result["error"].startswith("ExecuteError: Couldn't fetch the posting")
    assert result["harness_hash"]
