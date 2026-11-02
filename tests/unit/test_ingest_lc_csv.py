from comet.ingest.adapter import QRETCsvAdapter


def test_ingest_lc_csv():
    adapter = QRETCsvAdapter()

    run = adapter.ingest("tests/data/cold-flow-2026-03-06-slice.csv", tags={})

    assert len(run.channels) == 11
    assert run.channels["PTRun"].unit == "psi"
    assert run.channels["PTRun"].times[0] == 89170.0770
