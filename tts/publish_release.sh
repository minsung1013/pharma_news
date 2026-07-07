#!/usr/bin/env bash
# 생성된 MP3 를 GitHub Release(태그: $AUDIO_RELEASE_TAG) 애셋으로 업로드.
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
    --title "Narration audio" \
    --notes "국내 기사 낭독 오디오 (자동 생성)" \
    --prerelease
fi

gh release upload "$TAG" "${FILES[@]}" --clobber
echo "업로드 완료: ${#FILES[@]}개"
