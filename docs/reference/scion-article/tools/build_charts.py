"""차트 이미지 01, 05, 06을 SVG로 재구성한다.

사용: python -I tools/build_charts.py <article_dir>
- 01, 05: data/*.csv(digitize.py 결과, 근사값)를 사용한다.
- 06: 원본 이미지에 라벨로 적힌 값을 그대로 사용한다(정확값).
좌표계는 원본 이미지의 표시 크기(01/05: 2000x1125, 06: 1639x2000)와 같게 두었다.
"""
import csv
import datetime as dt
import sys
from pathlib import Path

BG, CARD, GRID, AXIS = "#E8E6DC", "#FAF9F5", "#E3E1D6", "#6B6A65"
INK, MUTED, LINE = "#141413", "#6B6A65", "#3D3D3A"
BLUE, ORANGE, GIT = "#5591CF", "#D97757", "#73726C"
FONT = "'Styrene B','Inter','Segoe UI',system-ui,sans-serif"

STYLE = f"""<style>
  text {{ font-family: {FONT}; fill: {MUTED}; }}
  .title {{ font-size: 64px; font-weight: 700; fill: {INK}; }}
  .sub {{ font-size: 34px; }}
  .tick {{ font-size: 24px; font-weight: 600; }}
  .legend {{ font-size: 26px; }}
</style>"""


def svg(w, h, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{label}">\n{STYLE}\n' + "\n".join(body) + "\n</svg>\n")


def fmt(n):
    return f"{n:,}"


def frame(title, sub):
    return [f'<rect width="2000" height="1125" fill="{BG}"/>',
            f'<text class="title" x="1000" y="100" text-anchor="middle">{title}</text>',
            f'<text class="sub" x="1000" y="150" text-anchor="middle">{sub}</text>',
            f'<rect x="36" y="196" width="1928" height="892" rx="28" fill="{CARD}"/>']


def time_axes(x0, px_day, y0, ytop, ymax, step, xend):
    out = []
    for v in range(0, ymax + 1, step):
        y = y0 - (y0 - ytop) * v / ymax
        if v:
            out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{xend}" y2="{y:.1f}" stroke="{GRID}" stroke-width="3"/>')
        out.append(f'<line x1="{x0 - 10}" y1="{y:.1f}" x2="{x0}" y2="{y:.1f}" stroke="{AXIS}" stroke-width="3"/>')
        out.append(f'<text class="tick" x="{x0 - 26}" y="{y + 9:.1f}" text-anchor="end">{fmt(v)}</text>')
    out.append(f'<line x1="{x0}" y1="{ytop}" x2="{x0}" y2="{y0}" stroke="{AXIS}" stroke-width="3"/>')
    out.append(f'<line x1="{x0}" y1="{y0}" x2="{xend}" y2="{y0}" stroke="{AXIS}" stroke-width="3"/>')
    for m in range(1, 10):
        x = x0 + (dt.date(2026, m, 1) - dt.date(2026, 1, 1)).days * px_day
        out.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y0 + 10}" stroke="{AXIS}" stroke-width="3"/>')
        out.append(f'<text class="tick" x="{x:.1f}" y="{y0 + 52}" text-anchor="middle">'
                   f'{dt.date(2026, m, 1):%b}</text>')
    return out


def stacked(x, w, y0, k, blue, orange, rx):
    out = []
    hb, ho = blue * k, orange * k
    if hb:
        out.append(f'<rect x="{x - w / 2:.1f}" y="{y0 - hb:.1f}" width="{w}" height="{hb:.1f}" rx="{rx}" fill="{BLUE}"/>')
    if ho:
        out.append(f'<rect x="{x - w / 2:.1f}" y="{y0 - hb - ho:.1f}" width="{w}" height="{ho:.1f}" rx="{rx}" fill="{ORANGE}"/>')
    return out


def legend(items, y):
    out = []
    for x, kind, label in items:
        if kind == "line":
            out.append(f'<line x1="{x}" y1="{y}" x2="{x + 44}" y2="{y}" stroke="{LINE}" stroke-width="5" stroke-linecap="round"/>')
            out.append(f'<text class="legend" x="{x + 58}" y="{y + 9}">{label}</text>')
        else:
            out.append(f'<rect x="{x}" y="{y - 15}" width="30" height="30" rx="5" fill="{kind}"/>')
            out.append(f'<text class="legend" x="{x + 46}" y="{y + 9}">{label}</text>')
    return out


def chart01(root):
    rows = list(csv.DictReader(open(root / "data/01-changes-merged-per-day.csv", encoding="utf-8")))
    data = {dt.date.fromisoformat(r["date"]): (int(r["pull_requests"]), int(r["antique_change_requests"])) for r in rows}
    x0, y0, ytop, ymax = 212, 898, 266, 35000
    px_day = (1805 - x0) / (dt.date(2026, 9, 1) - dt.date(2026, 1, 1)).days
    k = (y0 - ytop) / ymax
    b = frame("Changes merged per day", "Anthropic monorepo, January–September 2026")
    b += time_axes(x0, px_day, y0, ytop, ymax, 5000, 1897)
    for d, (blue, orange) in sorted(data.items()):
        b += stacked(x0 + (d - dt.date(2026, 1, 1)).days * px_day, 4.4, y0, k, blue, orange, 1)
    # 7일 이동평균(누락일은 0으로 간주)
    first, last = min(data), max(data)
    days = [first + dt.timedelta(i) for i in range((last - first).days + 1)]
    tot = [sum(data.get(d, (0, 0))) for d in days]
    pts = []
    for i, d in enumerate(days):
        win = tot[max(0, i - 6): i + 1]
        pts.append(f"{x0 + (d - dt.date(2026, 1, 1)).days * px_day:.1f},{y0 - sum(win) / len(win) * k:.1f}")
    b.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{LINE}" stroke-width="3.5" stroke-linejoin="round"/>')
    # 주석: Quiet week, 최고치 callout
    b.append(f'<line x1="1582" y1="726" x2="1582" y2="840" stroke="{AXIS}" stroke-width="3" stroke-dasharray="10 7"/>')
    b.append(f'<text x="1582" y="706" text-anchor="middle" font-size="26" font-weight="600">Quiet week</text>')
    b.append(f'<rect x="1594" y="349" width="238" height="102" rx="18" fill="{CARD}" stroke="{AXIS}" stroke-width="3"/>')
    b.append(f'<text x="1810" y="393" text-anchor="end" font-size="34" font-weight="700" style="fill:{LINE}">30,401</text>')
    b.append('<text x="1810" y="427" text-anchor="end" font-size="24">merged on Sep 9</text>')
    b += legend([(573, BLUE, "Pull requests"), (815, ORANGE, "Antique change requests"), (1200, "line", "7-day average")], 1013)
    return svg(2000, 1125, b, "Changes merged per day, Anthropic monorepo, January to September 2026")


def chart05(root):
    rows = list(csv.DictReader(open(root / "data/05-scion-antique-changes-per-week.csv", encoding="utf-8")))
    x0, y0, ytop, ymax = 192, 898, 266, 1600
    px_day = (1804 - x0) / (dt.date(2026, 9, 1) - dt.date(2026, 1, 1)).days
    k = (y0 - ytop) / ymax
    b = frame("Changes to the Scion and Antique codebases per week",
              "scm/ and antique/ directories of the Anthropic monorepo, January–September 2026")
    b[1] = b[1].replace('class="title"', 'class="title" style="font-size:58px"')
    b += time_axes(x0, px_day, y0, ytop, ymax, 200, 1897)
    for r in rows:
        d = dt.date.fromisoformat(r["week_start"])
        x = x0 + ((d - dt.date(2026, 1, 1)).days + 3.5) * px_day
        b += stacked(x, 36, y0, k, int(r["pull_requests"]), int(r["antique_change_requests"]), 3)
    b.append(f'<rect x="213" y="287" width="311" height="101" rx="18" fill="{CARD}" stroke="{AXIS}" stroke-width="3"/>')
    b.append(f'<text x="234" y="330" font-size="34" font-weight="700" style="fill:{LINE}">12,257</text>')
    b.append('<text x="234" y="364" font-size="24">changes since January</text>')
    b += legend([(706, BLUE, "Pull requests"), (948, ORANGE, "Antique change requests")], 1013)
    return svg(2000, 1125, b, "Changes to the Scion and Antique codebases per week, January to September 2026")


# 06: (라벨, git 값, git 라벨, scn 값, scn 라벨, 배수, 비고) — 값은 패널 축 단위
PANELS = [
    dict(title="Developer environments", legend=True, top=265, bottom=528, max=100, step=20, unit="s",
         rows=[("Pull latest", 87, "87 s", 3.5, "3.5 s", "×25", ""),
               ("Checkout", 15, "15 s", 1.1, "1.1 s", "×14", ""),
               ("Rebase", 13, "13 s", 2.7, "2.7 s", "×4.8", "")], ys=[310, 397, 484]),
    dict(title=None, top=597, bottom=858, max=4, step=1, unit="s",
         rows=[("Status", 3.9, "3.9 s", 0.019, "19 ms", "×207", ""),
               ("Commit", 1.4, "1.4 s", 1.1, "1.1 s", "×1.3", ""),
               ("Diff", 0.407, "407 ms", 0.067, "67 ms", "×6.1", "")], ys=[641, 728, 815]),
    dict(title="Agent environments", title_y=944, top=978, bottom=1328, max=8, step=2, unit="min",
         rows=[("New worktree", 7.1, "7.1 min", 5.1 / 60, "5.1 s", "×84", ""),
               ("Pull latest", 3.0, "3.0 min", 9.0 / 60, "9.0 s", "×20", ""),
               ("Commit", 18 / 60, "18 s", 0.761 / 60, "761 ms", "×24", ""),
               ("Status", 4.3 / 60, "4.3 s", 0.2 / 60, "&lt;0.2 s", "×20+", "")], ys=[1023, 1110, 1197, 1284]),
    dict(title="Total source control time per change request", title_y=1414, top=1448, bottom=1536, max=40, step=10,
         unit="min", rows=[("Agent environments", 34, "34 min", 3.7, "3.7 min", "×9.2", "≈11,000 agent hours a day")],
         ys=[1493]),
    dict(title="CI and compute jobs", title_y=1622, top=1655, bottom=1831, max=200, step=50, unit="s",
         rows=[("Checkout at start of compute job", 175, "175 s", 22, "22 s", "×8.0", "≈85,000 machine hours a day"),
               ("Checkout in a CI job", 31, "31 s", 3.5, "3.5 s", "×8.8", "≈195,000 machine hours a day")],
         ys=[1701, 1788]),
]


def chart06():
    X0, X1 = 462, 1140
    b = [f'<rect width="1639" height="2000" fill="{BG}"/>',
         f'<text x="819" y="90" text-anchor="middle" font-size="52" font-weight="700" style="fill:{INK}">'
         'Everyday source control commands on the monorepo</text>',
         f'<rect x="30" y="145" width="1579" height="1825" rx="24" fill="{CARD}"/>',
         f'<text x="1218" y="229" font-size="20" font-weight="600">Faster</text>']
    for p in PANELS:
        if p["title"]:
            ty = p.get("title_y", 228)
            b.append(f'<text x="{X0}" y="{ty}" font-size="27" font-weight="600" style="fill:{INK}">{p["title"]}</text>')
        if p.get("legend"):
            b.append(f'<rect x="943" y="196" width="197" height="46" rx="10" fill="none" stroke="{AXIS}" stroke-width="2.5"/>')
            b.append(f'<rect x="960" y="207" width="25" height="25" rx="4" fill="{GIT}"/>')
            b.append('<text x="997" y="227" font-size="21">git</text>')
            b.append(f'<rect x="1052" y="207" width="25" height="25" rx="4" fill="{ORANGE}"/>')
            b.append('<text x="1089" y="227" font-size="21">scn</text>')
        scale = (X1 - X0) / p["max"]
        for v in range(0, p["max"] + 1, p["step"]):
            x = X0 + v * scale
            if v:
                b.append(f'<line x1="{x:.1f}" y1="{p["top"]}" x2="{x:.1f}" y2="{p["bottom"]}" stroke="{GRID}" stroke-width="2.5"/>')
            b.append(f'<line x1="{x:.1f}" y1="{p["bottom"]}" x2="{x:.1f}" y2="{p["bottom"] + 8}" stroke="{AXIS}" stroke-width="2.5"/>')
            b.append(f'<text x="{x:.1f}" y="{p["bottom"] + 34}" text-anchor="middle" font-size="20" font-weight="600">'
                     f'{v} {p["unit"]}</text>')
        b.append(f'<line x1="{X0}" y1="{p["top"]}" x2="{X0}" y2="{p["bottom"]}" stroke="{AXIS}" stroke-width="2.5"/>')
        b.append(f'<line x1="{X0}" y1="{p["bottom"]}" x2="{X1}" y2="{p["bottom"]}" stroke="{AXIS}" stroke-width="2.5"/>')
        for (label, gv, gl, sv, sl, faster, note), y in zip(p["rows"], p["ys"]):
            gw, sw = gv * scale, sv * scale
            b.append(f'<text x="427" y="{y + 7}" text-anchor="end" font-size="20" font-weight="600">{label}</text>')
            b.append(f'<rect x="{X0}" y="{y - 29}" width="{gw:.1f}" height="28" rx="3" fill="{GIT}"/>')
            b.append(f'<rect x="{X0}" y="{y + 1}" width="{sw:.1f}" height="28" rx="3" fill="{ORANGE}"/>')
            b.append(f'<text x="{X0 + gw + 10:.1f}" y="{y - 8}" font-size="20" font-weight="600">{gl}</text>')
            b.append(f'<text x="{X0 + max(sw, 2) + 10:.1f}" y="{y + 22}" font-size="20" font-weight="600">{sl}</text>')
            b.append(f'<text x="1218" y="{y + 7}" font-size="20" font-weight="700" style="fill:{LINE}">{faster}</text>')
            if note:
                b.append(f'<text x="1288" y="{y + 7}" font-size="20">{note}</text>')
    b.append('<text x="800" y="1915" text-anchor="middle" font-size="20" font-weight="600">Median time</text>')
    return svg(1639, 2000, b, "Everyday source control commands on the monorepo: git versus scn median times")


def main(root):
    root = Path(root)
    out = root / "svg"
    out.mkdir(exist_ok=True)
    (out / "01-changes-merged-per-day.svg").write_text(chart01(root), encoding="utf-8")
    (out / "05-scion-antique-changes-per-week.svg").write_text(chart05(root), encoding="utf-8")
    (out / "06-command-performance.svg").write_text(chart06(), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
