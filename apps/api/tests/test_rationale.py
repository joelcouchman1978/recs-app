import pytest

from apps.api.app.spoiler_lint import assert_no_spoilers, SpoilerError
from apps.api.app.recs import build_rationale


class FakeItem:
    def __init__(self, gid, genres=None, tags=None, primary_genre="drama"):
        self.id = gid
        self.metadata = {"genres": genres or []}
        self.flags = tags or []
        self.primary_genre = primary_genre


class FF:
    def __init__(self, rp=0, tn=0, ha=0):
        self.rating_prior = rp
        self.tag_nudge = tn
        self.history_adj = ha


def test_spoiler_lint_blocks_denylist():
    with pytest.raises(SpoilerError):
        assert_no_spoilers("The killer is the butler in the season 2 finale")


def test_build_rationale_safe_and_short():
    item = FakeItem("x1", genres=["drama"], tags=["courtroom"]) 
    text = build_rationale(item, FF(rp=0.1, tn=0.1, ha=0.1), profile=None)
    assert text and len(text) <= 180


def test_build_rationale_raises_on_spoiler(monkeypatch):
    item = FakeItem("x2", genres=["drama"], tags=["courtroom"]) 
    from apps.api.app import recs as recs_mod
    # Force a spoiler by monkeypatching lint to always raise
    def boom(text):
        raise SpoilerError("bad")
    monkeypatch.setattr(recs_mod, "assert_no_spoilers", boom)
    with pytest.raises(SpoilerError):
        _ = recs_mod.build_rationale(item, FF(), profile=None)

