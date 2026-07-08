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


async def _synth_chunk(text: str, out: Path, voice: str | None = None) -> None:
    import edge_tts

    comm = edge_tts.Communicate(
        text,
        voice or config.EDGE_VOICE,
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


def synthesize(text: str, out_mp3: Path, voice: str | None = None) -> Path:
    """text 를 낭독하여 out_mp3(mp3) 로 저장하고 경로를 반환."""
    return synthesize_segments([(text, voice)], out_mp3)


def synthesize_segments(segments: list[tuple[str, str | None]], out_mp3: Path) -> Path:
    """(text, voice) 세그먼트 목록을 순서대로 낭독해 하나의 mp3 로 이어붙인다.

    voice 가 None 이면 config.EDGE_VOICE(기본 한국어)를 사용한다.
    한국어/영어 등 언어별 보이스를 세그먼트마다 다르게 줄 수 있다.
    """
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        parts: list[Path] = []
        idx = 0
        for text, voice in segments:
            if not text or not text.strip():
                continue
            for ch in _chunk(text):
                part = Path(td) / f"seg_{idx:04d}.mp3"
                asyncio.run(_synth_chunk(ch, part, voice))
                # 빈 오디오(합성 실패)면 건너뜀
                if part.exists() and part.stat().st_size > 0:
                    parts.append(part)
                    idx += 1
        if not parts:
            raise RuntimeError("합성된 오디오 세그먼트가 없습니다.")
        _concat_mp3(parts, out_mp3)
    return out_mp3
