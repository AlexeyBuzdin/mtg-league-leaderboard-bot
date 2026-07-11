import bot.__main__ as cli


def test_build_arg_parser_accepts_commands():
    parser = cli.build_parser()
    assert parser.parse_args(["ingest"]).command == "ingest"
    assert parser.parse_args(["leaderboard"]).command == "leaderboard"


def test_main_dispatches_ingest(monkeypatch):
    called = {}
    monkeypatch.setattr(cli, "_run_ingest", lambda cfg: called.setdefault("ingest", True))
    monkeypatch.setattr(cli, "load_config", lambda: object())
    cli.main(["ingest"])
    assert called == {"ingest": True}


def test_main_dispatches_leaderboard(monkeypatch):
    called = {}
    monkeypatch.setattr(cli, "_run_leaderboard", lambda cfg: called.setdefault("lb", True))
    monkeypatch.setattr(cli, "load_config", lambda: object())
    cli.main(["leaderboard"])
    assert called == {"lb": True}
