"""저장한 기사 HTML(<article>)을 Markdown으로 변환하고 이미지를 로컬 파일로 연결한다.

사용: python -I tools/html_to_md.py <page.html> <out.md> [svg_dir]
- 원문 사본은 저작권 때문에 로컬 전용 폴더(docs/internals/, .git/info/exclude)에만 둔다.
- svg_dir: out.md 기준 재구성 SVG 폴더의 상대 경로.
"""
import html
import re
import sys

URL = "https://www.anthropic.com/engineering/redesigning-source-control"
IMAGES = {  # 원본 CDN 해시 → 로컬 파일명
    "1e2a750dba61db4a76b72eec5b0cf50b8a7f878c": "01-changes-merged-per-day",
    "ff019752973f6d83d2f6ba3bf56636aced3ea82c": "02-git-scaling-setup",
    "71c83868210b4b571abb068ea4cd76de749566b1": "03-changeset-shape",
    "cba1eaaa67385fd00f210badaacd147de480120b": "04-checkout-architecture",
    "dd91296719203f38229824bb9bc9e9a61c76ed67": "05-scion-antique-changes-per-week",
    "c706fa6efb4b9e5cd2566cb080acbfce7218042d": "06-command-performance",
}


def inline(s):
    s = re.sub(r"<sup[^>]*>.*?>(\d+)</a></sup>", r"[^\1]", s, flags=re.S)
    s = re.sub(r"<a [^>]*href=\"#footnote-ref[^\"]*\".*?</a>", "", s, flags=re.S)
    s = re.sub(r"<a [^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"[\2](\1)", s, flags=re.S)
    # 강조 안쪽 끝 공백은 Markdown 강조를 깨뜨리므로 바깥으로 옮긴다
    s = re.sub(r"<(strong|em)>(\s*)(.*?)(\s*)</\1>",
               lambda m: m[2] + ("**" if m[1] == "strong" else "*") + m[3]
               + ("**" if m[1] == "strong" else "*") + m[4], s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


def main(src, dst, svg="../../reference/scion-article/svg"):
    page = open(src, encoding="utf-8").read()
    title = html.unescape(re.search(r"<title>\s*(.*?)\s*\\", page).group(1))
    date = re.search(r'<time dateTime="([^"]+)"', page).group(1)
    art = re.search(r"<article.*?</article>", page, re.S).group(0)
    out = [f"# {title}", "",
           f"> 원문: <{URL}>  ", f"> 게시: {date} · Engineering at Anthropic  ",
           f"> 보관 목적의 원문 사본입니다. 이미지는 `images/`(원본 PNG), 재구성 SVG는 `{svg}/`에 있습니다.", ""]
    for m in re.finditer(r"<(h2|h3|p|figure|ol)\b[^>]*>(.*?)</\1>", art, re.S):
        tag, body = m.group(1), m.group(2)
        if tag in ("h2", "h3"):
            out += [("## " if tag == "h2" else "### ") + inline(body), ""]
        elif tag == "p":
            text = inline(body)
            if text:
                out += [text, ""]
        elif tag == "figure":
            h = re.search(r"(\w{40})-\d+x\d+\.png", body).group(1)
            cap = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", body, re.S)
            cap = inline(cap.group(1)) if cap else ""
            name = IMAGES[h]
            out += [f"![{cap}](images/{name}.png)", "",
                    f"*{cap}* — 재구성 SVG: [`{name}.svg`]({svg}/{name}.svg)", ""]
        elif tag == "ol":
            for i, li in enumerate(re.findall(r"<li[^>]*>(.*?)</li>", body, re.S), 1):
                out += [f"[^{i}]: {inline(li)}", ""]
    open(dst, "w", encoding="utf-8").write("\n".join(out).rstrip() + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:4])
