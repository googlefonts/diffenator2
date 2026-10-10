from diffenator2 import shape


class _Stderr:
    def __init__(self, is_tty):
        self._is_tty = is_tty

    def isatty(self):
        return self._is_tty


def test_progress_bar_is_disabled_for_non_interactive_stderr(monkeypatch):
    calls = {}

    def fake_tqdm(iterable, **kwargs):
        calls.update(kwargs)
        return iterable

    monkeypatch.setattr(shape.sys, "stderr", _Stderr(False))
    monkeypatch.setattr(shape.tqdm, "tqdm", fake_tqdm)

    assert list(shape._progress_bar([1, 2], total=2)) == [1, 2]
    assert calls["disable"] is True
    assert calls["total"] == 2


def test_progress_bar_is_kept_for_interactive_stderr(monkeypatch):
    calls = {}

    def fake_tqdm(iterable, **kwargs):
        calls.update(kwargs)
        return iterable

    monkeypatch.setattr(shape.sys, "stderr", _Stderr(True))
    monkeypatch.setattr(shape.tqdm, "tqdm", fake_tqdm)

    assert list(shape._progress_bar([1, 2])) == [1, 2]
    assert calls["disable"] is False
