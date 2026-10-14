"""원본 PNG 막대 차트(01, 05)에서 픽셀을 읽어 근사 데이터를 CSV로 복원한다.

사용: python -I tools/digitize.py [article_dir] [images_dir]
- images_dir 기본값은 로컬 전용 원문 보관 폴더 docs/internals/scion-article/images 다(공개 저장소에는 없음).
- 파란 막대(Pull requests)가 아래, 주황 막대(Antique change requests)가 위로 쌓인 구조를 가정한다.
- 축 좌표(baseline, gridline, 월 tick)는 원본 3840px 해상도에서 측정한 값이다.
- 결과는 근사값이다(01: Sep 9 = 30,401 라벨로 보정, 05: 합계 오차 약 2%).
"""
import csv
import datetime as dt
import sys
from pathlib import Path

from PIL import Image


def classify(p):
    r, g, b = p
    if b > 170 and r < 130 and 110 < g < 180:
        return "B"
    if r > 190 and g < 150 and b < 120 and r - b > 80:
        return "O"
    if r < 120 and g < 120 and b < 120:
        return "D"  # 7일 평균선/축 등 어두운 선
    return None


def digitize(png, base_y, px_per_unit, x0, x1):
    im = Image.open(png).convert("RGB")
    px = im.load()
    cols = []
    for x in range(x0, x1):
        nb = no = gap = 0
        top = base_y
        y = base_y
        while y > 0:
            c = classify(px[x, y])
            if c == "B":
                nb += 1; gap = 0; top = y
            elif c == "O":
                no += 1; gap = 0; top = y
            elif c is None:
                gap += 1
                if gap > 3:
                    break
            y -= 1
        cols.append((x, nb, no, base_y - top))
    bars, cur = [], []
    for c in cols:
        if c[1] + c[2] > 0:
            cur.append(c)
        elif cur:
            bars.append(cur); cur = []
    if cur:
        bars.append(cur)
    out = []
    for b in bars:
        if len(b) < 4:
            continue
        mid = b[len(b) // 4: len(b) - len(b) // 4] or b
        h = max(c[3] for c in mid)
        nb = max(c[1] for c in mid)
        no = max(c[2] for c in mid)
        if nb + no == 0:
            continue
        out.append(((b[0][0] + b[-1][0]) / 2, h * nb / (nb + no) / px_per_unit, h * no / (nb + no) / px_per_unit))
    return out


def x_to_date(x, ticks):
    """ticks: [(px, date)] 월 tick 위치. 구간 선형 보간."""
    for (xa, da), (xb, db) in zip(ticks, ticks[1:]):
        if x <= xb or (xb, db) == ticks[-1]:
            return da + dt.timedelta(days=round((x - xa) / (xb - xa) * (db - da).days))


def month_ticks(xs):
    return [(x, dt.date(2026, m + 1, 1)) for m, x in enumerate(xs)]


def main(root, img=None):
    root = Path(root)
    img = Path(img) if img else root.parents[1] / "internals" / "scion-article" / "images"

    # 01: 일별 merge 수. 35,000 gridline y=509.5, 0 baseline y=1725.5 (원본 px)
    ppu = (1725.5 - 509.5) / 35000
    ticks = month_ticks([407.0, 797.5, 1149.5, 1539.5, 1917.5, 2307.5, 2685.0, 3075.0, 3465.5])
    bars = [b for b in digitize(img / "01-changes-merged-per-day.png", 1722, ppu, 412, 3640) if b[1] + b[2] >= 50]
    k = 30401 / sum(bars[-1][1:])  # 라벨 "30,401 merged on Sep 9"로 보정
    rows = {}
    for x, blue, orange in bars:
        d = x_to_date(x, ticks)
        rows[d] = (round(blue * k), round(orange * k))
    with open(root / "data" / "01-changes-merged-per-day.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "pull_requests", "antique_change_requests"])
        for d in sorted(rows):
            w.writerow([d.isoformat(), *rows[d]])

    # 05: 주별 변경 수. 1,600 gridline y=509.5, 0 baseline y=1725.5
    ppu = (1725.5 - 509.5) / 1600
    ticks = month_ticks([369.0, 763.5, 1120.0, 1515.0, 1897.0, 2291.5, 2673.5, 3068.5, 3463.5])
    bars = digitize(img / "05-scion-antique-changes-per-week.png", 1722, ppu, 375, 3640)
    with open(root / "data" / "05-scion-antique-changes-per-week.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["week_start", "pull_requests", "antique_change_requests"])
        for x, blue, orange in bars:
            # 막대 중심은 주 중간(목요일 부근). 가장 가까운 월요일로 맞춘다.
            d = x_to_date(x, ticks) - dt.timedelta(days=3)
            off = d.weekday() if d.weekday() <= 3 else d.weekday() - 7
            w.writerow([(d - dt.timedelta(days=off)).isoformat(), round(blue), round(orange)])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1],
         sys.argv[2] if len(sys.argv) > 2 else None)
