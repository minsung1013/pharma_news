"""edge-tts 한국어 낭독 엔진 (무료 · GPU 불필요).

- Microsoft Edge 뉴럴 보이스를 사용해 MP3 로 직접 출력.
- 장문은 문장 경계로 청킹 후 ffmpeg concat 으로 이어붙인다.
- 인터넷 연결 필요 (텍스트가 MS 서버로 전송됨).
"""
import asyncio
import logging
import re
import subprocess
import tempfile
from pathlib import Path

from . import config

log = logging.getLogger(__name__)

_MAX_CHARS = 1800  # 요청당 안전 길이
_SENT_SPLIT = re.compile(r"(?<=[.!?。…\n])\s+|(?<=다)\s+(?=[A-Z가-힣])")


def _chunk(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT.split(text) if p and p.strip()]
    chunks: list[str] = []
    cur = ""
    for p in parts:
        if len(cur) + len(p) + 1 > _MAX_CHARS:
            if cur:
                chunks.append(cur)
            # 단일 문장이 너무 길면 강제 분할
            while len(p) > _MAX_CHARS:
                chunks.append(p[:_MAX_CHARS])
                p = p[_MAX_CHARS:]
            cur = p
        else:
            cur = f"{cur} {p}".strip()
    if cur:
        chunks.append(cur)
    return chunks or [text[:_MAX_CHARS]]


async def _synth_chunk(text: str, out: Path) -> None:
    import edge_tts

    comm = edge_tts.Communicate(
        text,
        config.EDGE_VOICE,
        rate=config.EDGE_RATE,
        volume=config.EDGE_VOLUME,
    )
    await comm.save(str(out))


def _concat_mp3(parts: list[Path], out_mp3: Path) -> None:
    if len(parts) == 1:
        parts[0].replace(out_mp3)
        return
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as lf:
        for p in parts:
            lf.write(f"file '{p.as_posix()}'\n")
        list_path = lf.name
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", list_path, "-c", "copy", str(out_mp3)],
        check=True,
    )
    Path(list_path).unlink(missing_ok=True)


def synthesize(text: str, out_mp3: Path, speed: float | None = None) -> Path:
    """text 를 낭독하여 out_mp3(mp3) 로 저장하고 경로를 반환."""
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    chunks = _chunk(text)
    with tempfile.TemporaryDirectory() as td:
        parts: list[Path] = []
        for i, ch in enumerate(chunks):
            part = Path(td) / f"part_{i:03d}.mp3"
            asyncio.run(_synth_chunk(ch, part))
            parts.append(part)
        _concat_mp3(parts, out_mp3)
    return out_mp3
