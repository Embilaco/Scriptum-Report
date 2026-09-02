"""``scripts/convert_video.py``: what it converts, and what it must not.

The script turns a video into the three things a PowerPoint report needs — an
H.264 MP4, a poster frame (``python-pptx`` wants one for ``add_movie``), and a
metadata file carrying the dimensions. An **MP4 is accepted as input** for
exactly that reason: the video may already be the right format and still have
no poster frame and no metadata.

What it must not do is convert an MP4 into an MP4. Re-encoding costs quality
for nothing, and in place it handed ffmpeg one path to read and to write:
``-n`` made it refuse and the run carried on to the next step, ``--force``
made it ``-y`` and overwrite the input while still reading it.

ffmpeg and ffprobe are not run here. What is under test is the **decision** —
which of the three external calls is made, and on which file — so the three
are recorded instead, and the suite needs neither binary installed.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

TESTS_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = TESTS_ROOT.parent / 'scripts' / 'convert_video.py'

_spec = importlib.util.spec_from_file_location('convert_video', SCRIPT)
script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(script)


@pytest.fixture
def calls(monkeypatch):
    """ffmpeg and ffprobe recorded rather than run."""
    recorded = {'convert': [], 'poster': [], 'probe': []}

    def convert(source, target, force):
        recorded['convert'].append((Path(source), Path(target), force))
        Path(target).write_bytes(b'converted')

    def poster(video, destination, force):
        recorded['poster'].append((Path(video), Path(destination), force))
        Path(destination).write_bytes(b'poster')

    def probe(video):
        recorded['probe'].append(Path(video))
        return (640, 480)

    monkeypatch.setattr(script, 'convert_video', convert)
    monkeypatch.setattr(script, 'extract_poster_frame', poster)
    monkeypatch.setattr(script, 'probe_dimensions', probe)
    return recorded


def source(tmp_path, name):
    path = tmp_path / name
    path.write_bytes(b'not really a video')
    return path


# --------------------------------------------------- what it does convert

def test_a_video_is_converted_and_gets_its_poster_and_metadata(tmp_path, calls):
    clip = source(tmp_path, 'clip.avi')

    script.process_file(clip, None, force=False)

    assert calls['convert'] == [(clip, tmp_path / 'clip.mp4', False)]
    # the poster comes from the converted file, not from the source
    assert calls['poster'] == [(tmp_path / 'clip.mp4', tmp_path / 'clip_poster.jpg', False)]

    written = json.loads((tmp_path / 'clip.metadata.json').read_text(encoding='utf-8'))
    assert written == {'source': 'clip.avi', 'video': 'clip.mp4',
                       'poster_frame': 'clip_poster.jpg',
                       'width': 640, 'height': 480}


def test_an_existing_target_is_left_alone_without_force(tmp_path, calls):
    """Unchanged behaviour, kept honest beside the new rule."""
    source(tmp_path, 'clip.avi')
    (tmp_path / 'clip.mp4').write_bytes(b'converted earlier')

    script.process_file(tmp_path / 'clip.avi', None, force=False)

    assert calls['convert'] == []


# ------------------------------------------------ what it must not convert

def test_an_mp4_is_not_converted_but_still_gets_a_poster(tmp_path, calls):
    """The reason an MP4 is accepted at all: it may have no poster yet."""
    clip = source(tmp_path, 'clip.mp4')

    script.process_file(clip, None, force=False)

    assert calls['convert'] == [], 'an MP4 must not be re-encoded into itself'
    assert calls['poster'] == [(clip, tmp_path / 'clip_poster.jpg', False)]
    assert calls['probe'] == [clip]

    written = json.loads((tmp_path / 'clip.metadata.json').read_text(encoding='utf-8'))
    assert written['source'] == 'clip.mp4' and written['video'] == 'clip.mp4'
    assert clip.read_bytes() == b'not really a video', 'the input is untouched'


def test_force_does_not_re_encode_an_mp4_over_itself(tmp_path, calls):
    """The sharp edge. ``--force`` turns ffmpeg's ``-n`` into ``-y``, so the
    one call this rule prevents is the one that would have destroyed the
    input -- reading and writing the same path."""
    clip = source(tmp_path, 'clip.mp4')

    script.process_file(clip, None, force=True)

    assert calls['convert'] == []
    assert clip.read_bytes() == b'not really a video'


def test_an_mp4_into_an_output_dir_is_still_not_converted(tmp_path, calls):
    """With ``--output`` the target path differs from the source, so the
    exists-check could not have caught this one at all: the poster and the
    metadata are written to the output directory and the video stays where
    it is, named in the metadata as the file that was used."""
    clip = source(tmp_path, 'clip.mp4')
    elsewhere = tmp_path / 'out'

    script.process_file(clip, elsewhere, force=False)

    assert calls['convert'] == []
    assert calls['poster'] == [(clip, elsewhere / 'clip_poster.jpg', False)]

    written = json.loads((elsewhere / 'clip.metadata.json').read_text(encoding='utf-8'))
    assert written['video'] == 'clip.mp4'
    assert not (elsewhere / 'clip.mp4').exists()


def test_the_suffix_test_is_case_insensitive(tmp_path, calls):
    """A camera writing ``.MP4`` is the common way to meet this."""
    clip = source(tmp_path, 'clip.MP4')

    script.process_file(clip, None, force=False)

    assert calls['convert'] == []
