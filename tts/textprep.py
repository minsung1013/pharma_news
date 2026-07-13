"""낭독 전 최소 정제.

사용자 선택: '원문 전문 (그대로)'. 따라서 LLM 정제는 하지 않고,
스크래핑 노이즈(사이트 메뉴·구독/공유 버튼·섹션 라벨·바이라인·저작권 문구
·기자 이메일·이미지 캡션 등)만 정규식/휴리스틱으로 걷어낸다.

특히 뉴스 사이트 본문 앞에는 실제 기사 전에 아래 같은 '머리말(메뉴)'가 붙는다:
    Subscribe / BIOTECH / <제목> / By 홍길동 Jul 8, 2026 / <태그들> /
    Manage alerts for this article / Email this article / Share this article ...
이런 짧은 라벨성 줄을 '첫 실제 문단'이 나올 때까지 통째로 건너뛴다.
"""
import re

# 한 줄 통째로 버릴 패턴
#  - 국내 언론 공통 보일러플레이트(저작권·바이라인·공유·관련기사 등)
#  - 해외 뉴스 사이트 메뉴/구독/공유/섹션 라벨
_DROP_LINE = re.compile(
    r"("
    # 국내 언론 보일러플레이트
    r"저작권자|무단전재|재배포\s*금지|ⓒ|Copyright|All rights reserved"
    r"|기자\s*=|@[\w.\-]+\.(?:com|co\.kr|net)"          # 기자 바이라인/이메일
    r"|카카오|페이스북|트위터|네이버|밴드|공유하기|스크랩|인쇄"
    r"|관련기사|이전기사|다음기사|많이 본 기사|댓글"
    # 해외 뉴스 사이트 메뉴/구독/공유/광고 라벨
    r"|^Subscribe$|^Sign in$|^Log ?in$|^Brought to you by:?$"
    r"|^Advertisement$|^Sponsored$|^STAT\+?$|^STAT PLUS$"
    r"|Manage alerts for this article|Email this article|Share this article"
    r"|Print this article|Leave a comment|^Comments?$|^Share$|^Print$|^Save$"
    r")",
    re.IGNORECASE,
)

_IMG_CAPTION = re.compile(r"\[[^\]]*(?:사진|이미지|출처|자료|그래픽)[^\]]*\]")
_URL         = re.compile(r"https?://\S+")
_MULTISPACE  = re.compile(r"[ \t]+")
_MULTINL     = re.compile(r"\n{2,}")

# 첫 실제 문단으로 인정할 최소 길이(자). 뉴스 리드 문단은 대개 이보다 길다.
_PROSE_MIN_LEN = 100
# 머리말 스캔 상한(줄). 이 안에서 실제 문단을 못 찾으면 아무것도 건너뛰지 않는다(안전).
_PREAMBLE_SCAN_LIMIT = 20


def _strip_preamble(lines: list[str]) -> list[str]:
    """본문 앞의 메뉴/머리말(짧은 라벨성 줄)을 첫 실제 문단 전까지 제거."""
    for i, line in enumerate(lines[:_PREAMBLE_SCAN_LIMIT]):
        if len(line) >= _PROSE_MIN_LEN:
            return lines[i:] if i else lines
    # 첫 실제 문단을 못 찾았으면(전부 짧은 줄 등) 원본 유지
    return lines


def clean_for_tts(text: str) -> str:
    text = _IMG_CAPTION.sub(" ", text)
    text = _URL.sub(" ", text)

    kept: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if _DROP_LINE.search(s):
            continue
        kept.append(s)

    kept = _strip_preamble(kept)

    out = "\n".join(kept)
    out = _MULTISPACE.sub(" ", out)
    out = _MULTINL.sub("\n", out)
    return out.strip()
