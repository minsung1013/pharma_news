#!/usr/bin/env bash
# 생성된 에피소드 MP3 를 GitHub Release(태그: $AUDIO_RELEASE_TAG) 애셋으로 업로드.
# 하루 1개 에피소드 체계에 맞춰, 릴리스의 기존 애셋을 먼저 모두 지운 뒤 올린다
# (과거의 '기사당 mp3' 잔재 제거).
# GitHub Actions 에서 GH_TOKEN=secrets.GITHUB_TOKEN 로 실행된다.
set -euo pipefail
shopt -s nullglob

TAG="${AUDIO_RELEASE_TAG:-audio}"
FILES=(data/audio/*.mp3)

if [ ${#FILES[@]} -eq 0 ]; then
  echo "업로드할 오디오 없음 — 건너뜀"
  exit 0
fi

# 릴리스가 없으면 생성 (팟캐스트 오디오 보관용, prerelease)
if ! gh release view "$TAG" >/dev/null 2>&1; then
  gh release create "$TAG" \
    --title "흑염소 바이오 뉴스 — 에피소드 오디오" \
    --notes "자동 생성된 팟캐스트 에피소드(MP3) 보관용 릴리스" \
    --prerelease
fi

# 기존 애셋 정리 (오래된 mp3 잔재 제거). 최근 N일치는 feed.xml 기준으로 재업로드된다.
EXISTING=$(gh release view "$TAG" --json assets --jq '.assets[].name' 2>/dev/null || true)
for name in $EXISTING; do
  case "$name" in
    *.mp3)
      # 이번에 올릴 파일과 겹치면 --clobber 가 처리하므로 그대로 두고, 그 외 잔재만 삭제
      keep=0
      for f in "${FILES[@]}"; do
        [ "$(basename "$f")" = "$name" ] && keep=1 && break
      done
      if [ "$keep" -eq 0 ]; then
        echo "기존 애셋 삭제: $name"
        gh release delete-asset "$TAG" "$name" --yes || true
      fi
      ;;
  esac
done

gh release upload "$TAG" "${FILES[@]}" --clobber
echo "업로드 완료: ${#FILES[@]}개"
