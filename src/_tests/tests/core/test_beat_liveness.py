from pathlib import Path

from core.celery import BeatLiveness


class TestBeatLiveness:
    def test_touch_skipped_outside_beat(self, tmp_path: Path) -> None:
        path = tmp_path / 'beat-liveness'
        BeatLiveness(path).touch()
        assert not path.exists()

    def test_enable_creates_file(self, tmp_path: Path) -> None:
        path = tmp_path / 'beat-liveness'
        BeatLiveness(path).enable()
        assert path.exists()
