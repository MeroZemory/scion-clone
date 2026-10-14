# Scion 참고 자료: "Redesigning source control at Anthropic"

원문: <https://www.anthropic.com/engineering/redesigning-source-control> (2026-10-13 게시, 2026-10-15 수집)

| 경로 | 내용 |
|------|------|
| [structure-notes.md](structure-notes.md) | 그림 6장의 구조 해석과 설계 시사점(한국어) |
| `svg/` | 원문 그림 6장을 다시 그린 SVG |
| `data/` | 차트 01·05에서 픽셀로 복원한 근사 데이터(CSV) |
| `tools/` | 원문 보관·데이터 복원·SVG 생성 스크립트 |

## 원문 사본(로컬 전용)

원문 전문과 원본 그림은 저작권이 Anthropic에 있으므로 공개 저장소에 올리지 않습니다.
로컬에서는 `docs/internals/scion-article/`에 두고 `.git/info/exclude`로 제외합니다.

| 경로 | 내용 |
|------|------|
| `docs/internals/scion-article/source.html` | 수집한 원본 HTML |
| `docs/internals/scion-article/article.md` | 원문 Markdown(그림 위치·캡션·각주 포함) |
| `docs/internals/scion-article/images/` | 원본 PNG 6장(3840px) |

## 재생성

```sh
# 이 폴더에서 실행 (Pillow 필요). 원본 HTML과 PNG는 원문 URL에서 받아 internals에 둔다.
python -I tools/html_to_md.py ../../internals/scion-article/source.html ../../internals/scion-article/article.md
python -I tools/digitize.py        # internals의 images/01, 05 → data/*.csv
python -I tools/build_charts.py    # data + 라벨 값 → svg/01, 05, 06
```

`svg/02`·`03`·`04`(구조도)는 손으로 그린 파일이라 스크립트로 생성하지 않습니다.
