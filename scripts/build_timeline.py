"""Build the interactive timeline on the landing page from the survey's TikZ figure.

Reads Sections/timeline_figure.tex (cards, marks, influence arrows, axis labels, legend),
Sections/timeline_v3/papers.json (citation keys and first-release dates), citation_final.bib
(titles and authors), and map/paper_meta.json (arXiv ids and code links), then writes an
inline SVG into index.html between the <!-- timeline:start --> and <!-- timeline:end -->
markers. timeline.js adds the tooltips and highlighting. Coordinates are TikZ centimetres,
so the layout matches the paper figure exactly.

    python3 scripts/build_timeline.py [path/to/clm_survey_vN] [timeline_figure.tex]
"""
import html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SURVEY = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '..', '..', 'clm_survey_v9'))
FIGURE = sys.argv[2] if len(sys.argv) > 2 else 'timeline_figure.tex'
PAGE = os.path.join(ROOT, 'index.html')

sys.path.insert(0, os.path.join(ROOT, 'map'))
from build_map_data import parse_bib  # noqa: E402  (shared bib reader)

S = 40  # px per TikZ cm
PT = 1 / 28.4527  # TikZ pt in cm
X0, X1, Y1, Y0 = -1.0, 23.2, 4.85, -6.25  # figure bounds in TikZ coordinates
FAMILIES = {
    'vocabulary': 'Vocabulary embeddings',
    'contextual': 'Contextual embeddings',
    'compressed': 'Compressed latents',
    'onehot': 'One-hot',
    'binary': 'Binary',
    'simplex': 'Simplex',
    'sphere': 'Spherical',
    'foundation': 'Images and video',
    'neutral': 'Cross-cutting',
}
# Cards that are new or renamed since timeline_v3/papers.json was written.
EXTRA_KEYS = {
    'aFMLM': 'lee2026asynchronous',
    'FlowSeq': 'hu2024flow',
    'Diffinity': 'kim2026continuous',
    'FMLM+': 'agarwal2026posterior',
    'S/R-DMD': 'vankiem2026distribution',
    'MF-1': 'tao2026multimodal',
    'Clock Diffusion': 'schiff2026clock',
    'DoubleCat / SemiCat': 'davis2026design',
    'Auto-guidance': 'karras2024guiding',
    'Flow Map Self-Distill.': 'boffi2025build',
    'PDD': 'shaul2026parallel',
}
# Figure entries that citation_final.bib does not list, because the survey text does not cite them.
UNCITED = {
    'dhariwal2021diffusion': dict(title='Diffusion Models Beat GANs on Image Synthesis', authors=['Prafulla Dhariwal', 'Alex Nichol'], venue='NeurIPS'),
    'karras2022elucidating': dict(title='Elucidating the Design Space of Diffusion-Based Generative Models', authors=['Tero Karras', 'Miika Aittala', 'Timo Aila', 'Samuli Laine'], venue='NeurIPS'),
    'rombach2022high': dict(title='High-Resolution Image Synthesis with Latent Diffusion Models', authors=['Robin Rombach', 'Andreas Blattmann', 'Dominik Lorenz', 'Patrick Esser', 'Björn Ommer'], venue='CVPR'),
}
# The figure's transfer curves carry no names, so they are listed here in drawing order.
INFLUENCES = [
    ('DDPM', 'Diffusion-LM'), ('VDM', 'Plaid'), ('LDM', 'LD4LG'), ('EDM', 'CDCD'), ('SiD', 'DLM-One'),
    ('Flow Map Matching', 'FLM / FMLM'), ('Diffusion Forcing', 'Sigma'), ('BTM', 'DBTM'), ('DMD', 'S/R-DMD'), ('PDD', 'Sigma'),
]
MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def X(x):
    return round((float(x) - X0) * S, 2)


def Y(y):
    return round((Y1 - float(y)) * S, 2)


def esc(s):
    return html.escape(str(s), quote=True)


def plain(label):
    """A TikZ card label as a plain name, for example 'FLM / FMLM'."""
    s = re.sub(r'-\\\\', '-', label).replace('\\\\', ' ').replace('$^\\star$', '*').replace('$', '')
    return re.sub(r'\s+', ' ', s).strip()


def label_svg(tex):
    """TikZ card label to SVG tspans: line breaks, $x$ italics, and ^\\star."""
    def inline(s):
        s = esc(s)
        s = re.sub(r'\$\^\\star\$', '<tspan class="tl-sup" dy="-3">\u22c6</tspan><tspan dy="3"></tspan>', s)
        return re.sub(r'\$([a-z])\$', r'<tspan class="tl-math">\1</tspan>', s)
    return [inline(line.strip()) for line in tex.split('\\\\')]


def nice_date(d):
    m = re.match(r'(\d{4})(?:-(\d\d))?(?:-(\d\d))?$', d or '')
    if not m:
        return 'Forthcoming'
    y, mo, day = m.groups()
    if mo and day:
        return f'{MONTHS[int(mo) - 1]} {int(day)}, {y}'
    return f'{MONTHS[int(mo) - 1]} {y}' if mo else y


def legend_entries(tex):
    """Legend rows from the TikZ source. TeX measures the column gaps, so they are estimated here."""
    block = tex[tex.index('% Legend, top row'):]
    swatch = r'^\\path\[(\w+),rounded corners[^\]]*\] \(\\tvLegendX([A-E]),(-[\d.]+)\) rectangle \(\{[^}]*\},(-[\d.]+)\);%\n'
    mark = r'^\\fill\[(tvFewStep|tvGuide)\] \(\{\\tvLegendX([A-E])[^}]*\},(-[\d.]+)\)[^\n]*\n'
    node = r'\\node\[anchor=base west,[^\]]*\] at \(\{[^}]*\},(-[\d.]+)\) \{(.*?)\};'
    rows = [dict(kind='swatch', fam=f, col=c, y0=float(a), y1=float(b), base=float(u), text=t)
            for f, c, a, b, u, t in re.findall(swatch + node, block, re.M)]
    rows += [dict(kind='mark', fam=f, col=c, y0=float(a), base=float(u), text=t)
             for f, c, a, u, t in re.findall(mark + node, block, re.M)]
    width = {c: .57 + max(len(r['text']) * 11.4 * .53 / S for r in rows if r['col'] == c) for c in 'ABCDE'}
    span = 23.91
    gap = (span - sum(width.values())) / 4
    x, left = -0.905, {}
    for c in 'ABCDE':
        left[c] = x
        x += width[c] + gap
    for r in rows:
        r['x'] = left[r['col']]
    return rows


def main():
    tex = open(os.path.join(SURVEY, 'Sections', FIGURE), encoding='utf-8').read()
    bib = parse_bib(open(os.path.join(SURVEY, 'citation_final.bib'), encoding='utf-8').read())
    roster = json.load(open(os.path.join(SURVEY, 'Sections', 'timeline_v3', 'papers.json'), encoding='utf-8'))['papers']
    meta = json.load(open(os.path.join(ROOT, 'map', 'paper_meta.json'), encoding='utf-8'))
    by_label = {re.sub(r'\s+', '', p['label']).lower(): p for p in roster}
    num = r'(-?[\d.]+)'
    out = []

    # Panels, winter band, and lane headings.
    panels = re.findall(r'^\\path\[fill=white,[^\]]*\] \(' + num + ',' + num + r'\) rectangle \(' + num + ',' + num + r'\);', tex, re.M)
    for x0, y0, x1, y1 in panels:
        out.append(f'<rect class="tl-panel" x="{X(x0)}" y="{Y(y1)}" width="{X(x1) - X(x0):.2f}" height="{Y(y0) - Y(y1):.2f}" rx="{.77 * PT * S:.2f}"/>')
    band = re.search(r'^\\path\[fill=tvVocabularyLine,fill opacity=[\d.]+\] \(' + num + ',' + num + r'\) rectangle \(' + num + ',' + num + r'\);', tex, re.M)
    if band:
        x0, y0, x1, y1 = band.groups()
        out.append(f'<rect class="tl-winter" x="{X(x0)}" y="{Y(y1)}" width="{X(x1) - X(x0):.2f}" height="{Y(y0) - Y(y1):.2f}"/>')
    for x, y, text in re.findall(r'^\\node\[font=\\tvWinter[^\]]*\] at \(' + num + ',' + num + r'\)\s*\{(.*?)\};', tex, re.M):
        text = text.replace('``', '\u201c').replace("''", '\u201d')
        out.append(f'<text class="tl-winter-label" x="{X(x)}" y="{Y(y)}">{esc(text)}</text>')
    for x, y, text in re.findall(r'^\\node\[anchor=base west,font=\\tvHeading[^\]]*\] at \(' + num + ',' + num + r'\) \{(.*?)\};', tex, re.M):
        out.append(f'<text class="tl-heading" x="{X(x)}" y="{Y(y)}">{esc(text)}</text>')

    # Cards (parsed first so the arrows can name their endpoints).
    cards = re.findall(r'^\\tvCard\{(\w+)\}\{(\w+)\}\{' + num + r'\}\{' + num + r'\}\{([\d.]+)\}\{(.*?)\}\{(.*)\}%$', tex, re.M)
    assert len(cards) == len(re.findall(r'^\\tvCard\{', tex, re.M)), 'a card did not parse'
    by_name = {plain(c[5]): c for c in cards}

    # Influence arrows sit under the cards, like the TikZ drawing order.
    curves = re.findall(r'^\\draw\[tvOnehotLine,[^\n]*?\] \(' + num + ',' + num + r'\) \.\. controls \(' + num + ',' + num +
                        r'\) and \(' + num + ',' + num + r'\) \.\. \(' + num + ',' + num + r'\);', tex, re.M)
    assert len(curves) == len(INFLUENCES), f'{len(curves)} curves in the figure, {len(INFLUENCES)} names in INFLUENCES'
    arrows = []
    for (a, b), p in zip(INFLUENCES, curves):
        xs, ys = p[0::2], p[1::2]
        assert abs(float(xs[0]) - float(by_name[a][2])) < .5 and abs(float(xs[3]) - float(by_name[b][2])) < .5, f'{a} -> {b} does not match its curve'
        d = f'M{X(xs[0])},{Y(ys[0])} C{X(xs[1])},{Y(ys[1])} {X(xs[2])},{Y(ys[2])} {X(xs[3])},{Y(ys[3])}'
        arrows.append(f'<path class="tl-arrow" d="{d}" data-from="{esc(by_name[a][0])}" data-to="{esc(by_name[b][0])}" marker-end="url(#tl-head)"><title>{esc(a)} \u2192 {esc(b)}</title></path>')

    # Axis, stems, and ticks.
    axis = re.search(r'^\\draw\[tvInk,[^\n]*?\] \(' + num + ',' + num + r'\) -- \(' + num + ',' + num + r'\);', tex, re.M)
    out.append(f'<line class="tl-axis" x1="{X(axis.group(1))}" y1="{Y(0)}" x2="{X(axis.group(3)) - 4}" y2="{Y(0)}" marker-end="url(#tl-axis-head)"/>')
    for x0, y0, x1, y1 in re.findall(r'^\\draw\[tvStem,[^\]]*\] \(' + num + ',' + num + r'\) -- \(' + num + ',' + num + r'\);', tex, re.M):
        out.append(f'<line class="tl-stem" x1="{X(x0)}" y1="{Y(y0)}" x2="{X(x1)}" y2="{Y(y1)}"/>')
    out.extend(arrows)
    for x, y in re.findall(r'^\\fill\[tvInk\] \(' + num + ',' + num + r'\) circle', tex, re.M):
        out.append(f'<circle class="tl-tick" cx="{X(x)}" cy="{Y(y)}" r="{.045 * S:.2f}"/>')
    fs = 7.75 * PT * S
    for x, y, text in re.findall(r'^\\node\[fill=tvPurple,[^\]]*\] at \(' + num + ',' + num + r'\) \{(.*?)\};', tex, re.M):
        text = text.replace('--', '\u2013')
        w = len(text) * fs * .56 + 8 * PT * S
        out.append(f'<g class="tl-year"><rect x="{X(x) - w / 2:.2f}" y="{Y(y) - fs * .8:.2f}" width="{w:.2f}" height="{fs * 1.6:.2f}"/>'
                   f'<text x="{X(x)}" y="{Y(y)}">{esc(text)}</text></g>')
    for x, y, text in re.findall(r'^\\node\[fill=tvOuter,[^\]]*\] at \(' + num + ',' + num + r'\) \{(.*?)\};', tex, re.M):
        text = text.replace('--', '\u2013')
        w = len(text) * fs * .5 + 4 * PT * S
        out.append(f'<g class="tl-month"><rect x="{X(x) - w / 2:.2f}" y="{Y(y) - fs * .7:.2f}" width="{w:.2f}" height="{fs * 1.4:.2f}"/>'
                   f'<text x="{X(x)}" y="{Y(y)}">{esc(text)}</text></g>')

    # Cards with their guidance and few-step marks.
    w = 1.49 * S
    line_h = 8.2 * PT * S
    r = .071 * S
    for cid, fam, x, y, h, label, marks in cards:
        name = plain(label)
        entry = by_label.get(re.sub(r'\s+', '', name).lower(), {})
        key = EXTRA_KEYS.get(name) or entry.get('bibkey')
        ref, info = bib.get(key) or UNCITED.get(key), meta.get(key, {})
        assert ref, f'{name}: no citation key ({key})'
        arxiv = info.get('arxiv', '')
        url = f'https://arxiv.org/abs/{arxiv}' if arxiv else ref.get('url', '')
        date = entry.get('date') if re.match(r'\d{4}', entry.get('date') or '') else info.get('published', '')
        guide = 'fill=tvGuide' in marks
        few = 'fill=tvFewStep' in marks
        authors = ref.get('authors', [])
        byline = (authors[0] + (' et al.' if len(authors) > 2 else f' and {authors[1]}' if len(authors) == 2 else '')) if authors else ''
        hh = float(h) * S
        cx, cy = X(x), Y(y)
        lines = label_svg(label)
        first = cy - (len(lines) - 1) * line_h / 2
        tspans = ''.join(f'<tspan x="{cx}" y="{first + i * line_h:.2f}">{t}</tspan>' for i, t in enumerate(lines))
        dots = ''
        right, top = cx + w / 2, cy - hh / 2
        if few:
            dots += f'<rect class="tl-dot tl-dot-few" x="{right - .316 * S:.2f}" y="{top - r:.2f}" width="{2 * r:.2f}" height="{2 * r:.2f}"/>'
        if guide:
            dots += f'<circle class="tl-dot tl-dot-guide" cx="{right - .077 * S:.2f}" cy="{top:.2f}" r="{r:.2f}"/>'
        attrs = {
            'class': f'tl-card f-{fam}' + (' has-guide' if guide else '') + (' has-few' if few else ''),
            'id': f'tl-{cid}', 'data-name': name, 'data-date': nice_date(date),
            'data-family': FAMILIES[fam], 'data-title': ref.get('title', ''), 'data-authors': byline,
            'data-venue': ref.get('venue', ''), 'data-arxiv': arxiv, 'data-code': info.get('code', ''),
        }
        if url:
            attrs.update({'href': url, 'target': '_blank', 'rel': 'noopener'})
        attr = ' '.join(f'{k}="{esc(v)}"' for k, v in attrs.items() if v != '')
        tag = 'a' if url else 'g tabindex="0"'
        out.append(f'<{tag} {attr} aria-label="{esc(name)}, {esc(attrs["data-date"])}">'
                   f'<rect class="tl-box" x="{cx - w / 2:.2f}" y="{cy - hh / 2:.2f}" width="{w:.2f}" height="{hh:.2f}" rx="{1.29 * PT * S:.2f}"/>'
                   f'<text class="tl-label">{tspans}</text>{dots}</{tag.split()[0]}>')

    # Legend: each entry filters the cards.
    for e in legend_entries(tex):
        tx, ty = e['x'] + .57, e['base'] + .1
        hit = f'<rect class="tl-hit" x="{X(e["x"]) - 4:.2f}" y="{Y(ty) - 10:.2f}" width="{.57 * S + len(e["text"]) * 6.3 + 10:.2f}" height="20"/>'
        if e['kind'] == 'swatch':
            out.append(f'<g class="tl-legend f-{e["fam"]}" data-filter="f-{e["fam"]}" role="button" tabindex="0" aria-pressed="false">{hit}'
                       f'<rect x="{X(e["x"])}" y="{Y(e["y1"])}" width="{.465 * S:.2f}" height="{Y(e["y0"]) - Y(e["y1"]):.2f}" rx="{1.29 * PT * S:.2f}"/>'
                       f'<text x="{X(tx)}" y="{Y(ty)}">{esc(e["text"])}</text></g>')
        else:
            few = e['fam'] == 'tvFewStep'
            my = Y(e['y0']) - .09 * S if few else Y(e['y0'])
            mark = (f'<rect class="tl-dot tl-dot-few" x="{X(e["x"] + .1425):.2f}" y="{my - .09 * S:.2f}" width="{.18 * S:.2f}" height="{.18 * S:.2f}"/>' if few
                    else f'<circle class="tl-dot tl-dot-guide" cx="{X(e["x"] + .2325):.2f}" cy="{my:.2f}" r="{.09 * S:.2f}"/>')
            out.append(f'<g class="tl-legend" data-filter="{"has-few" if few else "has-guide"}" role="button" tabindex="0" aria-pressed="false">{hit}{mark}'
                       f'<text x="{X(tx)}" y="{Y(ty)}">{esc(e["text"])}</text></g>')

    caption = re.search(r'\\captionof\{figure\}\{(.*?)\}%', tex)
    width, height = (X1 - X0) * S, (Y1 - Y0) * S
    head = .194 * S
    svg = (f'<svg class="tl" viewBox="0 0 {width:.0f} {height:.0f}" role="group" aria-labelledby="tl-caption">'
           f'<defs><marker id="tl-head" viewBox="0 0 10 8" refX="9" refY="4" markerUnits="userSpaceOnUse" markerWidth="{head:.1f}" markerHeight="{head * .8:.1f}" orient="auto">'
           f'<path d="M0,0 L10,4 L0,8 L2.6,4 Z"/></marker>'
           f'<marker id="tl-axis-head" viewBox="0 0 10 8" refX="2" refY="4" markerUnits="userSpaceOnUse" markerWidth="{head:.1f}" markerHeight="{head * .8:.1f}" orient="auto">'
           f'<path d="M0,0 L10,4 L0,8 L2.6,4 Z"/></marker></defs>'
           + ''.join(out) + '</svg>')
    block = (f'<!-- timeline:start (generated by scripts/build_timeline.py from {FIGURE}; do not edit by hand) -->\n'
             f'      <figure class="hero-figure timeline-figure">\n'
             f'        <div class="tl-scroll" tabindex="0" aria-label="Timeline, scroll sideways on small screens">{svg}\n'
             f'          <div class="tl-tip" hidden></div>\n'
             f'        </div>\n'
             f'        <figcaption id="tl-caption">{esc(caption.group(1) if caption else "Timeline")} '
             f'Hover or tap a paper for links, or select a legend entry to highlight a family. Dashed arrows mark direct adaptations to language.</figcaption>\n'
             f'      </figure>\n      <!-- timeline:end -->')
    page = open(PAGE, encoding='utf-8').read()
    start, end = page.find('<!-- timeline:start'), page.find('<!-- timeline:end -->')
    assert start >= 0 and end > start, 'index.html needs the <!-- timeline:start --> and <!-- timeline:end --> markers'
    page = page[:start] + block + page[end + len('<!-- timeline:end -->'):]
    open(PAGE, 'w', encoding='utf-8').write(page)
    print(f'{len(cards)} cards, {len(arrows)} arrows from {FIGURE}')


if __name__ == '__main__':
    main()
