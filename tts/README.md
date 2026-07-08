# 흑염소 바이오 뉴스 — 팟캐스트

매일 수집한 제약·바이오·AI 뉴스를 무료 TTS(`edge-tts`)로 낭독해 **하루 한 개의 에피소드**
(MP3)로 만들고 **팟캐스트 RSS 피드**로 배포합니다. 폰의 팟캐스트 앱으로 스트리밍·
백그라운드 재생·오프라인 저장·배속·이어듣기가 됩니다.

## 에피소드 구성 (하루 1개)

`main.py` 가 남긴 `data/digest_<date>.json` 을 읽어 아래 순서로 이어 낭독합니다.

1. **인트로** — "YYYY년 M월 D일, 흑염소 바이오 뉴스 브리핑입니다."
2. **핵심 하이라이트** — 상위 하이라이트 상세 요약 (한국어)
3. **오늘의 종합** — 빅파마·바이오텍 주요 움직임 (한국어)
4. **전체 기사 요약** — 오늘 수집된 모든 기사 한 문장 요약 (한국어)
5. **주요 뉴스 원문** — 규칙(AI·M&A·협업) 상위 기사 원문 낭독.
   **한국어 기사는 한국어 보이스, 영어 기사는 영어 보이스.** `PODCAST_TARGET_MIN`(기본 30분)
   에 도달할 때까지 우선순위대로 채웁니다.

> 기사당 파일 1개가 아니라 **하루 1개 에피소드**만 생성합니다.
> 메일 다이제스트에서 원문 낭독에 채택된 기사는 `🎙 PODCAST` 배지로 표시됩니다.

## 완전 서버리스 — PC는 꺼져 있어도 됩니다

`edge-tts`는 Microsoft 뉴럴 보이스를 호출하는 **무료 API**라 GPU도 로컬 서버도 필요 없습니다.
생성·호스팅을 전부 GitHub 위에서 처리합니다.

```
[GitHub Actions] 매일 06:00 KST (자동)
   main.py 디제스트
   → tts.make_audio : 국내 기사 스크래핑 → edge-tts → MP3
   → GitHub Release(tag: audio) 에 MP3 업로드
   → data/audio/feed.xml + episodes.json 커밋
        │
        ▼
[모바일 팟캐스트 앱] 아래 피드 URL 구독 → 스트리밍
```

## 구독하기 (폰)

피드 URL:

```
https://raw.githubusercontent.com/minsung1013/pharma_news/main/data/audio/feed.xml
```

- **Android — AntennaPod**: 검색창(➕) → “Add Podcast by URL” → 위 URL
- **iOS — Apple Podcasts**: 라이브러리 → 우상단 “…” → “URL로 프로그램 추가”
- **Pocket Casts / Overcast 등**: “Add by URL / RSS” 메뉴에 붙여넣기

> 첫 구독은 워크플로가 한 번 이상 실행되어 `feed.xml`이 생성된 뒤에 가능합니다.

## 활성화 (최초 1회)

1. 변경사항 푸시:
   ```bash
   git add -A && git commit -m "feat: 국내 기사 TTS 팟캐스트" && git push
   ```
2. 즉시 실행: GitHub 저장소 → **Actions → BioPharma Digest → Run workflow**
   (또는 매일 06:00 KST 스케줄 대기)
3. 실행 후 위 피드 URL을 팟캐스트 앱에 등록.

별도 시크릿/카드 등록 불필요 — `edge-tts`는 키가 필요 없고, 릴리스 업로드는
Actions 기본 `GITHUB_TOKEN`으로 처리됩니다.

## 설정 (환경변수)

`digest.yml` 의 `env:` 또는 로컬 `.env` 에서:

| 변수 | 기본값 | 설명 |
|---|---|---|
| `EDGE_VOICE` | `ko-KR-SunHiNeural` | 한국어 목소리. 남성은 `ko-KR-InJoonNeural` |
| `EDGE_VOICE_EN` | `en-US-AriaNeural` | 영어 원문 낭독 목소리 |
| `EDGE_RATE` | `+0%` | 낭독 속도. 예 `+15%` |
| `EDGE_VOLUME` | `+0%` | 음량 |
| `PODCAST_TARGET_MIN` | `30` | 목표 분량(분). 주요뉴스 원문을 이 시간까지 채움 |
| `PODCAST_MAX_FULLTEXT` | `15` | 원문 낭독 최대 기사 수(상한) |
| `PODCAST_TITLE` | `흑염소 바이오 뉴스` | 팟캐스트 제목 |
| `FEED_RETENTION_DAYS` | `30` | 피드에 유지할 최근 일수 |
| `AUDIO_RELEASE_TAG` | `audio` | 오디오 릴리스 태그 |

커버 아트는 `data/audio/cover.png` (repo 커밋). 재생성: `python -m tts.make_cover`.

## 로컬 미리듣기 (옵션)

PC에서 바로 확인하고 싶을 때만:

```bash
# 전용 venv
python -m venv .venv-tts
.venv-tts\Scripts\pip install -r tts/requirements.txt
.venv-tts\Scripts\python -m playwright install chromium

# 다이제스트 데이터 생성 (메일 발송 없이 data/digest_<date>.json 만)
.venv-tts\Scripts\python main.py --dry-run

# 오디오 생성 (오늘자 에피소드 1개)
.venv-tts\Scripts\python -m tts.make_audio

# 로컬 서버로 재생 (http://localhost:8080)
set AUDIO_BASE_URL=http://127.0.0.1:8080/audio
.venv-tts\Scripts\python -m tts.server
```

## 구성 파일

| 파일 | 역할 |
|---|---|
| `podcast_select.py` | 원문 낭독 선별 규칙(AI·M&A·협업) 점수화 + 길이 추정 |
| `tts/make_audio.py` | 오케스트레이터: `digest_<date>.json` → 세그먼트 낭독 → 1개 에피소드 |
| `tts/engine.py` | edge-tts 래퍼 (언어별 보이스 + 문장 청킹 + ffmpeg concat) |
| `tts/textprep.py` | 낭독 전 최소 정제 (저작권/공유버튼/캡션 제거) |
| `tts/feed.py` | RSS(feed.xml) 생성(커버·iTunes 태그 포함), `episodes.json` 관리 |
| `tts/make_cover.py` | 커버 아트(흑염소) PNG 생성 |
| `tts/server.py` | 로컬 미리듣기용 Flask 서버 (Range 지원) |
| `tts/publish_release.sh` | MP3 → GitHub Release 업로드 (기존 애셋 정리 후, CI용) |
| `tts/config.py` | 경로·음성·호스팅 설정 |

## 참고

- `edge-tts`는 드물게 GitHub Actions IP에서 일시 차단될 수 있습니다. 이 경우
  오디오 단계만 실패하고(‑ `continue-on-error`) 메일 디제스트는 정상 발송됩니다.
  필요 시 로컬에서 `python -m tts.make_audio` 후 수동 배포하면 됩니다.
- MP3는 git에 저장하지 않습니다(`.gitignore`). 릴리스 애셋으로만 보관되고,
  `feed.xml`·`episodes.json`만 커밋되어 상태가 유지됩니다.
