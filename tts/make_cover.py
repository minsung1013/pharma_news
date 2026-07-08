"""팟캐스트 커버 아트(cute 흑염소) 생성 → data/audio/cover.png (1500x1500).

SVG 일러스트를 Chromium(Playwright)으로 래스터화한다. Apple/Spotify 팟캐스트는
정사각 PNG(≥1400px)를 요구하므로 SVG 가 아닌 PNG 로 굽는다.

실행: python -m tts.make_cover
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tts import config  # noqa: E402

SIZE = 1500

_SVG = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="0 0 1500 1500">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#fef6e4"/>
      <stop offset="55%" stop-color="#f7efe0"/>
      <stop offset="100%" stop-color="#d9ecd6"/>
    </linearGradient>
    <radialGradient id="cheek" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#f6a9a9" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="#f6a9a9" stop-opacity="0"/>
    </radialGradient>
    <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="14" stdDeviation="18" flood-color="#000" flood-opacity="0.18"/>
    </filter>
  </defs>

  <rect width="1500" height="1500" fill="url(#bg)"/>
  <circle cx="750" cy="600" r="470" fill="#ffffff" opacity="0.55"/>

  <g filter="url(#soft)">
    <!-- Horns -->
    <path d="M598 352 C 520 250, 470 150, 520 96 C 566 150, 604 246, 648 330 Z" fill="#8d8d97"/>
    <path d="M902 352 C 980 250, 1030 150, 980 96 C 934 150, 896 246, 852 330 Z" fill="#8d8d97"/>
    <path d="M600 350 C 540 268, 502 190, 522 128" fill="none" stroke="#6f6f79" stroke-width="10" stroke-linecap="round"/>
    <path d="M900 350 C 960 268, 998 190, 978 128" fill="none" stroke="#6f6f79" stroke-width="10" stroke-linecap="round"/>

    <!-- Ears -->
    <g transform="rotate(28 470 560)">
      <ellipse cx="470" cy="560" rx="120" ry="66" fill="#2c2c33"/>
      <ellipse cx="486" cy="560" rx="70" ry="34" fill="#d98a9a"/>
    </g>
    <g transform="rotate(-28 1030 560)">
      <ellipse cx="1030" cy="560" rx="120" ry="66" fill="#2c2c33"/>
      <ellipse cx="1014" cy="560" rx="70" ry="34" fill="#d98a9a"/>
    </g>

    <!-- Head -->
    <ellipse cx="750" cy="620" rx="300" ry="330" fill="#2c2c33"/>
    <!-- Top fur tuft -->
    <path d="M700 320 q20 -60 50 -70 q30 10 50 70 q-50 -22 -100 0 Z" fill="#3a3a42"/>

    <!-- Cheeks -->
    <circle cx="590" cy="720" r="70" fill="url(#cheek)"/>
    <circle cx="910" cy="720" r="70" fill="url(#cheek)"/>

    <!-- Eyes -->
    <ellipse cx="648" cy="612" rx="74" ry="86" fill="#ffffff"/>
    <ellipse cx="852" cy="612" rx="74" ry="86" fill="#ffffff"/>
    <circle cx="656" cy="626" r="42" fill="#1a1a1f"/>
    <circle cx="844" cy="626" r="42" fill="#1a1a1f"/>
    <circle cx="642" cy="610" r="15" fill="#ffffff"/>
    <circle cx="830" cy="610" r="15" fill="#ffffff"/>

    <!-- Muzzle -->
    <ellipse cx="750" cy="790" rx="168" ry="128" fill="#4a4a52"/>
    <!-- Nose -->
    <ellipse cx="750" cy="756" rx="52" ry="34" fill="#e7a0ad"/>
    <!-- Smile -->
    <path d="M690 828 q60 58 120 0" fill="none" stroke="#202026" stroke-width="12" stroke-linecap="round"/>
    <!-- Goatee -->
    <path d="M712 906 q38 96 38 150 q0 -54 38 -150 q-38 22 -76 0 Z" fill="#3a3a42"/>
  </g>

  <!-- Title -->
  <text x="750" y="1180" text-anchor="middle"
        font-family="'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif"
        font-size="146" font-weight="800" fill="#2c2c33">흑염소 바이오 뉴스</text>
  <text x="750" y="1288" text-anchor="middle"
        font-family="'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif"
        font-size="56" font-weight="500" fill="#6b6b73" letter-spacing="4">제약 · 바이오 · AI 뉴스 브리핑</text>
</svg>
"""

_HTML = f"""<!doctype html><html><head><meta charset="utf-8">
<style>*{{margin:0;padding:0}} html,body{{width:{SIZE}px;height:{SIZE}px}}</style>
</head><body>{_SVG}</body></html>"""


def main() -> None:
    from playwright.sync_api import sync_playwright

    out = config.COVER_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": SIZE, "height": SIZE},
                                device_scale_factor=1)
        page.set_content(_HTML, wait_until="networkidle")
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": SIZE, "height": SIZE})
        browser.close()
    print(f"커버 생성: {out} ({out.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
