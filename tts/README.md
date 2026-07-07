# 국내 기사 TTS 낭독 → 모바일 팟캐스트

국내(바이오타임즈·BRIC) 기사 **원문**을 무료 TTS(`edge-tts`)로 낭독한 MP3를 만들고,
**팟캐스트 RSS 피드**로 배포합니다. 폰의 팟캐스트 앱으로 스트리밍·백그라운드 재생·
오프라인 저장·배속·이어듣기가 됩니다.

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
| `EDGE_VOICE` | `ko-KR-SunHiNeural` | 목소리. 남성은 `ko-KR-InJoonNeural` |
| `EDGE_RATE` | `+0%` | 낭독 속도. 예 `+15%` |
| `EDGE_VOLUME` | `+0%` | 음량 |
| `FEED_RETENTION_DAYS` | `30` | 피드에 유지할 최근 일수 |
| `AUDIO_RELEASE_TAG` | `audio` | 오디오 릴리스 태그 |

낭독 대상 매체는 `tts/config.py` 의 `KOREAN_HOSTS` 에서 조정합니다.

## 로컬 미리듣기 (옵션)

PC에서 바로 확인하고 싶을 때만:

```bash
# 전용 venv
python -m venv .venv-tts
.venv-tts\Scripts\pip install -r tts/requirements.txt
.venv-tts\Scripts\python -m playwright install chromium

# 오디오 생성 (오늘자, 2건만 테스트)
.venv-tts\Scripts\python -m tts.make_audio --limit 2

# 로컬 서버로 재생 (http://localhost:8080)
set AUDIO_BASE_URL=http://127.0.0.1:8080/audio
.venv-tts\Scripts\python -m tts.server
```

## 구성 파일

| 파일 | 역할 |
|---|---|
| `tts/make_audio.py` | 오케스트레이터: 스크래핑 → TTS → 피드/에피소드 갱신 |
| `tts/engine.py` | edge-tts 래퍼 (문장 청킹 + ffmpeg concat) |
| `tts/textprep.py` | 낭독 전 최소 정제 (저작권/공유버튼/캡션 제거) |
| `tts/feed.py` | RSS(feed.xml) 생성, `episodes.json` 관리 |
| `tts/server.py` | 로컬 미리듣기용 Flask 서버 (Range 지원) |
| `tts/publish_release.sh` | MP3 → GitHub Release 업로드 (CI용) |
| `tts/config.py` | 경로·음성·호스팅 설정 |

## 참고

- `edge-tts`는 드물게 GitHub Actions IP에서 일시 차단될 수 있습니다. 이 경우
  오디오 단계만 실패하고(‑ `continue-on-error`) 메일 디제스트는 정상 발송됩니다.
  필요 시 로컬에서 `python -m tts.make_audio` 후 수동 배포하면 됩니다.
- MP3는 git에 저장하지 않습니다(`.gitignore`). 릴리스 애셋으로만 보관되고,
  `feed.xml`·`episodes.json`만 커밋되어 상태가 유지됩니다.
