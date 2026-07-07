"""낭독 전 최소 정제.

사용자 선택: '원문 전문 (그대로)'. 따라서 LLM 정제는 하지 않고,
스크래핑 노이즈(저작권 문구·기자 이메일·공유버튼 텍스트·이미지 캡션 등)만
정규식으로 걷어낸다.
"""
import re

# 한 줄 통째로 버릴 패턴 (BioTimes 등 국내 언론 공통 보일러플레이트)
_DROP_LINE = re.compile(
    r"("
    r"저작권자|무단전재|재배포\s*금지|ⓒ|Copyright|All rights reserved"
    r"|기자\s*=|@[\w.\-]+\.(?:com|co\.kr|net)"          # 기자 바이라인/이메일
    r"|카카오|페이스북|트위터|네이버|밴드|공유하기|스크랩|인쇄"
    r"|관련기사|이전기사|다음기사|많이 본 기사|댓글"
    r")",
    re.IGNORECASE,
)

_IMG_CAPTION = re.compile(r"\[[^\]]*(?:사진|이미지|출처|자료|그래픽)[^\]]*\]")
_URL         = re.compile(r"https?://\S+")
_MULTISPACE  = re.compile(r"[ \t]+")
_MULTINL     = re.compile(r"\n{2,}")


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

    out = "\n".join(kept)
    out = _MULTISPACE.sub(" ", out)
    out = _MULTINL.sub("\n", out)
    return out.strip()
