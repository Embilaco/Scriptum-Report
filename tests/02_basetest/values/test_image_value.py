"""Tests for :mod:`rdf.values.image_value`."""

from pathlib import Path

from _setup_values import *

# ``ImageValue`` depends on Pillow. Provide a light-weight stub when Pillow is not
# installed so the module can be imported in isolation.
try:  # pragma: no cover - optional dependency guard
    import PIL  # type: ignore  # noqa: F401
    import PIL.Image  # type: ignore  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - executed only when Pillow missing
    pil_module = types.ModuleType("PIL")
    pil_image_module = types.ModuleType("PIL.Image")
    pil_image_module.open = lambda filename: None  # type: ignore[assignment]
    pil_module.Image = pil_image_module  # type: ignore[attr-defined]
    sys.modules.setdefault("PIL", pil_module)
    sys.modules.setdefault("PIL.Image", pil_image_module)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    workdir = tmp_path / "workspace"
    workdir.mkdir()
    ensure_link(DATA_SOURCE, workdir / "data")
    return workdir


def _write_rdf(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines))
    return path


def _image_task(rdf) -> object:
    return next(task for task in rdf.tasks if task.target == "image:preview")


def test_image_value_temperatures_dimensions(monkeypatch: pytest.MonkeyPatch, workspace: Path) -> None:
    """Existing images are loaded and expose their dimensions."""

    target_image = workspace / "data" / "camera.png"
    assert target_image.exists(), "sample image must be available for the test"

    class DummyImage:
        def __init__(self, size: tuple[int, int]):
            self.size = size

    def fake_open(filename: str) -> DummyImage:
        assert Path(filename).name == target_image.name
        return DummyImage((640, 480))

    monkeypatch.chdir(workspace)
    monkeypatch.setattr(sys.modules["PIL.Image"], "open", fake_open)

    rdf_path = _write_rdf(
        workspace / "image.rdf",
        [
            "*version=100",
            "*documenttype=docx",
            "*datadir=./data",
            "section:figures",
            ".image:preview=file:camera.png",
        ],
    )

    rdf = ReportDataFile(str(rdf_path), _root=[])
    task = _image_task(rdf)
    task.value.load()

    assert task.value.content.size == (640, 480)
    assert task.value.object.width == 640
    assert task.value.object.height == 480


def test_image_value_missing_file_returns_placeholder(
    monkeypatch: pytest.MonkeyPatch, workspace: Path
) -> None:
    """Missing image files produce a descriptive placeholder string."""

    monkeypatch.chdir(workspace)
    rdf_path = _write_rdf(
        workspace / "image_missing.rdf",
        [
            "*version=100",
            "*documenttype=docx",
            "*datadir=./data",
            "section:figures",
            ".image:preview=file:not_available.png",
        ],
    )

    rdf = ReportDataFile(str(rdf_path), _root=[])
    task = _image_task(rdf)
    task.value.load()

    assert "no file with image" in task.value.content, f"Asserion error: not found 'no file with image' in '{task.value.content}'"
    assert not task.value.object.exists


def test_image_value_propagates_open_errors(monkeypatch: pytest.MonkeyPatch, workspace: Path) -> None:
    """Failures from ``Image.open`` bubble up for the caller to handle."""

    target_image = workspace / "data" / "camera.png"
    assert target_image.exists(), "sample image must be available for the test"

    def raising_open(filename: str) -> None:
        raise OSError("bad image")

    monkeypatch.chdir(workspace)
    monkeypatch.setattr(sys.modules["PIL.Image"], "open", raising_open)

    rdf_path = _write_rdf(
        workspace / "image_error.rdf",
        [
            "*version=100",
            "*documenttype=docx",
            "*datadir=./data",
            "section:figures",
            ".image:preview=file:camera.png",
        ],
    )

    rdf = ReportDataFile(str(rdf_path), _root=[])
    task = _image_task(rdf)

    with pytest.raises(OSError):
        task.value.load()
