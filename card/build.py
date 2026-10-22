#!/usr/bin/env python3
"""Builds dark_mode.svg and light_mode.svg for the profile README.

Left column: an ASCII portrait that prints line by line, top to bottom.
Right column: a neofetch-style summary.

    python card/build.py                                  # stats fetched with `gh`
    python card/build.py --contributions 2569 --commits 2212

The portraits live in card/art/. dark.txt is a positive (dense background), which reads
right on a dark page; light.txt is its negative, which reads right on a light page, and
gets its stray background dots removed. Standard library only; fetching the stats needs
the GitHub CLI (`gh`) logged in as the profile owner, so private contributions count.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

LOGIN = "winker-zb"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# ── Layout: one 20 px line grid shared by both columns ───────────────────────
FONT_PX = 16
LINE_PX = 20
LINES = 25
MARGIN = 28
TOP = 38
INFO_X = 481        # room for the portrait even in wider monospace fonts (Menlo)
WIDTH = 1055
HEIGHT = 542
INFO_COLS = 56
VALUE_COL = 26
FONTS = "ConsolasFallback,Consolas,SFMono-Regular,Menlo,Monaco,'Liberation Mono','Courier New',monospace"

# ── Printing animation ───────────────────────────────────────────────────────
START_S = 0.4
STEP_S = 0.075
STATUS_PX = 11

THEMES = {
    "dark_mode.svg": dict(art="dark.txt", clean=False, bg="#0d1117", border="#30363d", portrait="#3fb950",
                          flash="#d2ffd8", status="#3fb950", txt="#e6edf3", key="#3fb950", value="#e6edf3",
                          dots="#3d444d", head="#56d364"),
    "light_mode.svg": dict(art="light.txt", clean=True, bg="#f6f8fa", border="#d0d7de", portrait="#1a7f37",
                           flash="#6fdd8b", status="#1a7f37", txt="#1f2328", key="#1a7f37", value="#1f2328",
                           dots="#afb8c1", head="#116329"),
}


# ── Summary ──────────────────────────────────────────────────────────────────
def pair(key, value):
    return [("key", key), ("txt", ": "), ("dots", "." * (VALUE_COL - len(key) - 3) + " "), ("value", value)]


def more(value):
    return [("txt", " " * VALUE_COL), ("value", value)]


def section(name):
    return [("txt", "- "), ("key", name), ("dots", " " + "─" * (INFO_COLS - len(name) - 3))]


def summary(contributions, commits):
    rows = [
        [("head", LOGIN), ("txt", "@"), ("head", "github"), ("dots", " " + "─" * 39)],
        pair("Role", "Founder & builder"),
        pair("Host", "ZAMA GROUP"),
        pair("OS", "Windows 11"),
        pair("IDE", "Claude Code"),
        [],
        pair("Languages", "TypeScript, SQL, JavaScript"),
        pair("Stack.Web", "Next.js, React, Tailwind CSS"),
        pair("Stack.Data", "Supabase, PostgreSQL"),
        pair("Stack.Cloud", "Vercel, GitHub Actions"),
        [],
        section("Projects"),
        pair("ZAMA", "Commerce OS for fashion retail"),
        more("storefront · POS · inventory"),
        pair("NANIS", "Self-discovery through the"),
        more("universe, astrology & arcana"),
        pair("Next", "more in the making"),
        [],
        section("Focus"),
        pair("Building", "Multi-tenant SaaS, payments"),
        pair("Exploring", "AI-assisted engineering"),
        [],
        section("GitHub Stats"),
        pair("Contributions", f"{contributions:,} (last 12 months)"),
        pair("Commits", f"{commits:,} (last 12 months)"),
    ]
    if len(rows) != LINES:
        sys.exit(f"the summary has {len(rows)} rows; the grid has {LINES}")
    for row in rows:
        if sum(len(t) for _, t in row) > INFO_COLS:
            sys.exit(f"summary row wider than {INFO_COLS} columns: {''.join(t for _, t in row)!r}")
    return rows


def fetch_stats():
    """Contributions and commits in the last 12 months, as the owner sees them (private included)."""
    query = ('query($login:String!){user(login:$login){contributionsCollection{'
             'totalCommitContributions contributionCalendar{totalContributions}}}}')
    try:
        out = subprocess.run(["gh", "api", "graphql", "-f", f"query={query}", "-F", f"login={LOGIN}"],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        sys.exit(f"could not fetch the stats with gh ({error}); pass --contributions and --commits")
    data = json.loads(out)["data"]["user"]["contributionsCollection"]
    return data["contributionCalendar"]["totalContributions"], data["totalCommitContributions"]


# ── Portrait ─────────────────────────────────────────────────────────────────
def load_art(name, clean):
    lines = [line.rstrip() for line in (HERE / "art" / name).read_text(encoding="utf-8").splitlines()]
    return clean_background(lines) if clean else lines


def clean_background(lines):
    """Drops stray background dots: a '.' with nothing but spaces or dots around it (5×3)."""
    width = max(len(line) for line in lines)
    grid = [line.ljust(width) for line in lines]
    out = []
    for y, line in enumerate(grid):
        chars = list(line)
        for x, c in enumerate(line):
            if c != ".":
                continue
            around = [grid[yy][xx] for yy in range(max(0, y - 1), min(len(grid), y + 2))
                      for xx in range(max(0, x - 2), min(width, x + 3))]
            if all(a in " ." for a in around):
                chars[x] = " "
        out.append("".join(chars).rstrip())
    return out


def geometry(lines):
    """Font size, line height and origin that fit the portrait in the left column undistorted."""
    cols, rows = max(len(line) for line in lines), len(lines)
    usable = INFO_X - MARGIN - 12
    top, bottom = 24, TOP + (LINES - 1) * LINE_PX - 18
    font = min(10.0, usable / (cols * 0.6))          # fits even a 0.6em-wide font
    line = min(font * 0.58 / 0.54, (bottom - top) / rows)   # ~0.54 cell aspect, as the art was made
    x = MARGIN + (usable - cols * font * 0.55) / 2
    y0 = top + ((bottom - top) - rows * line) / 2 + line * 0.8
    return dict(font=round(font, 2), line=round(line, 2), x=round(x, 1), y0=round(y0, 1), step=min(STEP_S, 3.2 / rows))


def status(k, n):
    if k == n:
        return f"> portrait.svg  {n}/{n} lines  [done]"
    return f"> portrait.svg  line {k}/{n}  [printing {round(100 * k / n)}%]"


# ── SVG ──────────────────────────────────────────────────────────────────────
def svg(theme, art, rows):
    n = len(art)
    geo = geometry(art)
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" font-family="{FONTS}" font-size="{FONT_PX}px">',
        f"<title>{LOGIN}</title>",
        "<style>"
        f".key{{fill:{theme['key']}}}.value{{fill:{theme['value']}}}.dots{{fill:{theme['dots']}}}"
        f".head{{fill:{theme['head']};font-weight:bold}}.txt{{fill:{theme['txt']}}}"
        "text,tspan{white-space:pre}"
        # each line is born bright and settles into the portrait colour, like a print head
        f".l{{opacity:0;fill:{theme['portrait']};animation:print .6s ease-out forwards}}"
        f"@keyframes print{{0%{{opacity:1;fill:{theme['flash']}}}100%{{opacity:1;fill:{theme['portrait']}}}}}"
        # the counter: each text shows only in its own time slot; the last one stays
        f".st{{opacity:0;fill:{theme['status']};animation-name:slot;animation-timing-function:linear}}"
        ".st.done{animation:stay .01s linear forwards}"
        "@keyframes slot{from{opacity:1}to{opacity:1}}"
        "@keyframes stay{to{opacity:1}}"
        "@media (prefers-reduced-motion:reduce){.l{animation:none;opacity:1}.st{animation:none}.st.done{animation:none;opacity:1}}"
        "</style>",
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="12" fill="{theme["bg"]}" stroke="{theme["border"]}"/>',
        f'<text x="{geo["x"]}" y="{geo["y0"]}" font-size="{geo["font"]}px" xml:space="preserve">',
    ]
    step = geo["step"]
    for i, line in enumerate(art):
        out.append(f'<tspan class="l" style="animation-delay:{START_S + i * step:.3f}s" x="{geo["x"]}" y="{round(geo["y0"] + i * geo["line"], 2)}">{escape(line)}</tspan>')
    out.append("</text>")
    y_status = TOP + (LINES - 1) * LINE_PX
    for k in range(n + 1):
        text = escape(status(k, n))
        if k == n:
            out.append(f'<text class="st done" style="animation-delay:{START_S + (n - 1) * step:.3f}s" x="{MARGIN}" y="{y_status}" font-size="{STATUS_PX}px" xml:space="preserve">{text}</text>')
        else:
            begin = 0.0 if k == 0 else START_S + (k - 1) * step
            length = START_S if k == 0 else step
            out.append(f'<text class="st" style="animation-delay:{begin:.3f}s;animation-duration:{length:.3f}s" x="{MARGIN}" y="{y_status}" font-size="{STATUS_PX}px" xml:space="preserve">{text}</text>')
    out.append(f'<text x="{INFO_X}" y="{TOP}" xml:space="preserve">')
    for i, row in enumerate(rows):
        if row:
            parts = "".join(f'<tspan class="{c}">{escape(t)}</tspan>' for c, t in row)
            out.append(f'<tspan x="{INFO_X}" y="{TOP + i * LINE_PX}">{parts}</tspan>')
    out.append("</text>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contributions", type=int, help="contributions in the last 12 months (default: ask gh)")
    parser.add_argument("--commits", type=int, help="commits in the last 12 months (default: ask gh)")
    args = parser.parse_args()
    if (args.contributions is None) != (args.commits is None):
        parser.error("pass both --contributions and --commits, or neither")
    contributions, commits = (args.contributions, args.commits) if args.commits is not None else fetch_stats()
    rows = summary(contributions, commits)
    for name, theme in THEMES.items():
        art = load_art(theme["art"], theme["clean"])
        (ROOT / name).write_text(svg(theme, art, rows), encoding="utf-8", newline="\n")
        print(f"{name}: {len(art)} portrait lines, {contributions:,} contributions, {commits:,} commits")


if __name__ == "__main__":
    main()
