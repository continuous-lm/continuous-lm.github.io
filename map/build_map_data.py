"""Build data.js for the paper map.

Reads titles, authors, and venues from citation_final.bib, and the citing sentences and
co-citations from the section .tex files that main.tex inputs. paper_meta.json holds the
curated arXiv ids, code links, and short overviews. The curated category of each
continuous language model is below.
Positions come from hand-placed cluster centers, a within-cluster PCA of TF-IDF
features (title + survey sentences), and a short collision relaxation.

    python3 build_map_data.py [path/to/clm_survey_vN]   # default: ../../../clm_survey_v9
"""
import html, json, math, os, re, sys, urllib.parse
from collections import Counter, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SURVEY = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', '..', 'clm_survey_v9'))
SKIP_INPUTS = ('abstract', 'table', 'taxonomy', 'timeline')  # floats and lists, not prose

# Clusters: id, label, center on a roughly 1050 x 750 canvas.
CATS = [
    ('emb',     'Vocabulary embeddings',     (390, 190)),
    ('latent',  'Contextual & latent spaces', (120, 340)),
    ('simplex', 'Simplex & sphere',           (680, 80)),
    ('onehot',  'One-hot, binary & flow maps', (880, 290)),
    ('fewstep', 'Few-step & one-step',        (880, 580)),
    ('hybrid',  'Hybrid & scheduled',         (590, 380)),
    ('guide',   'Guidance & inference',       (560, 640)),
    ('apps',    'Reasoning, multimodal & evaluation', (250, 620)),
]

# key: (category, short name)
PAPERS = {
    # Token embeddings
    'li2022diffusion': ('emb', 'Diffusion-LM'),
    'gong2022diffuseq': ('emb', 'DiffuSeq'),
    'yuan2022seqdiffuseq': ('emb', 'SeqDiffuSeq'),
    'lin2023text': ('emb', 'GENIE'),
    'dieleman2022continuous': ('emb', 'CDCD'),
    'gulrajani2023likelihood': ('emb', 'Plaid'),
    'yang2026continuous': ('emb', 'RePlaid'),
    'gao2022empowering': ('emb', 'Difformer'),
    'chen2026langflow': ('emb', 'LangFlow'),
    'yang2026large': ('emb', 'Sigma'),
    'chavan2026large': ('emb', 'Lafa'),
    'li2026convergeflow': ('emb', 'ConvergeFlow'),
    'kouzelis2026self': ('emb', 'SERF'),
    'liu2024text': ('emb', 'TREC'),
    'luo2026designing': ('emb', 'LangDiT'),
    'shabalin2025smoothie': ('emb', 'Smoothie'),
    'su2026rectified': ('emb', 'ReLF'),
    'raya2026noise': ('emb', 'InfoNoise'),
    # Contextual & latent
    'strudel2022self': ('latent', 'SED'),
    'shabalin2025tencdm': ('latent', 'TEncDM'),
    'shen2026codar': ('latent', 'CoDAR'),
    'hu2026elf': ('latent', 'ELF'),
    'li2026elf': ('latent', 'ELF-REG'),
    'guo2026deltaflow': ('latent', 'DeltaFlow'),
    'zhang2026scaling': ('latent', 'Diffusibility'),
    'lovelace2023latent': ('latent', 'LD4LG'),
    'zhang2023planner': ('latent', 'PLANNER'),
    'lovelace2024diffusion': ('latent', 'DGLM'),
    'meshchaninov2026cosmos': ('latent', 'Cosmos'),
    'jiang2026textldm': ('latent', 'TextLDM'),
    'meshchaninov2026train': ('latent', 'LDLM'),
    'guo2026continuous': ('latent', 'Cola DLM'),
    'liang2026aurora': ('latent', 'AURORA-LM'),
    'dong2026language': ('latent', 'Manta-LM'),
    'du2026continuous': ('latent', 'Decoder Interface'),
    'feng2026denoising': ('latent', 'BLD'),
    'yuan2026one': ('latent', 'JPEG-DLM'),
    'ollu2026denoising': ('latent', 'H-CoBit'),
    'guo2026cola2': ('latent', 'Cola2'),
    'he2026rethinking': ('latent', 'PSF'),
    'barrault2024large': ('latent', 'LCM'),
    'peng2026don': ('latent', 'Representation Alignment'),
    'zhu2025segment': ('latent', 'SLD'),
    # Simplex & sphere
    'han2023ssd': ('simplex', 'SSD-LM'),
    'han2024david': ('simplex', 'SSD-2'),
    'mahabadi2024tess': ('simplex', 'TESS'),
    'tae2025tess2': ('simplex', 'TESS 2'),
    'graves2023bayesian': ('simplex', 'BFN'),
    'stark2024dirichlet': ('simplex', 'Dirichlet FM'),
    'avdeyev2023dirichlet': ('simplex', 'DDSM'),
    'tang2025gumbel': ('simplex', 'Gumbel-Softmax FM'),
    'davis2024fisher': ('simplex', 'Fisher-Flow'),
    'jo2026continuous': ('simplex', 'RDLM'),
    'deschenaux2026simplex': ('simplex', 'SDM'),
    'deschenaux2026language': ('simplex', 'S-FLM'),
    'chemseddine2026spherical': ('simplex', 'Spherical Flows'),
    'miele2026spherical': ('simplex', 'SBD'),
    'jia2026llaco': ('simplex', 'LLaCO'),
    # One-hot flows & flow maps
    'lee2026flow': ('onehot', 'FLM / FMLM'),
    'roos2026categorical': ('onehot', 'CFM'),
    'davis2026scaling': ('onehot', 'Scaling CFM'),
    'potaptchik2026discrete': ('onehot', 'DFM'),
    'tang2026discrete': ('onehot', 'DBTM'),
    'tang2026expanding': ('onehot', 'EFlows / EFM'),
    'lee2026asynchronous': ('onehot', 'aFLM / aFMLM'),
    'yoo2026self': ('onehot', 'FMLM*'),
    'agarwal2026posterior': ('onehot', 'FMLM+'),
    'azangulov2026masked': ('onehot', 'MLFM'),
    'chen2022analog': ('onehot', 'Analog Bits'),
    'batzolis2026cobit': ('onehot', 'CoBit'),
    'zhuang2026bitlm': ('onehot', 'BitLM'),
    'eijkelboom2024variational': ('onehot', 'CatFlow'),
    'oba2026bct': ('onehot', 'BCT'),
    # Few-step & one-step
    'zhang2024language': ('fewstep', 'LF'),
    'hu2024flow': ('fewstep', 'FlowSeq'),
    'liu2024enable': ('fewstep', 'FMSeq'),
    'chen2025dlm': ('fewstep', 'DLM-One'),
    'zhang2026flowlm': ('fewstep', 'FlowLM'),
    'warczynski2026onestep': ('fewstep', 'Shortcut FM'),
    'peng2026coupling': ('fewstep', 'Coupling Models'),
    'eijkelboom2026categorical': ('fewstep', 'Categorical Drifting'),
    'li2026onestep': ('fewstep', 'R-WGF'),
    'liu2026onestep': ('fewstep', 'Seq-Drifting'),
    'kim2026gumbel': ('fewstep', 'GSF'),
    'zhang2026gumbel': ('fewstep', 'Gumbel Distillation'),
    'draxler2026parallel': ('fewstep', 'PTP'),
    'shao2025continuous': ('fewstep', 'CALM'),
    'drobyshevskiy2026representation': ('fewstep', 'Rep-MMD'),
    'semenov2026latent': ('fewstep', 'CoFlow'),
    'draxler2026parallel2': ('fewstep', 'PLM'),
    'lee2026beckmann': ('fewstep', 'BTM'),
    'vankiem2026distribution': ('fewstep', 'S/R-DMD'),
    'nguyen2026fastdiss': ('fewstep', 'FastDiSS'),
    # Hybrid & scheduled
    'sahoo2025diffusion': ('hybrid', 'Duo'),
    'pynadath2025candi': ('hybrid', 'CANDI'),
    'zheng2026cadd': ('hybrid', 'CADD'),
    'zhou2025ccdd': ('hybrid', 'CCDD'),
    'lemercier2026diladiff': ('hybrid', 'DiLaDiff'),
    'wang2026masked': ('hybrid', 'x-Prediction Flow'),
    'yu2026dsl': ('hybrid', 'DSL-LLaDA'),
    'bansal2026token': ('hybrid', 'TTCD'),
    'wu2023ar': ('hybrid', 'AR-Diffusion'),
    'bhatt2026generating': ('hybrid', 'Random CSPs'),
    'jutras2026sticky': ('hybrid', 'Sticky Jumps'),
    'schiff2026clock': ('hybrid', 'Clock Diffusion'),
    'ren2026hierarchical': ('hybrid', 'HC-DLM'),
    'gong2023diffuseqv2': ('hybrid', 'DiffuSeq-v2'),
    'li2025unifying': ('hybrid', 'NeoDiff'),
    'uziel2026crocodil': ('hybrid', 'CRoCoDiL'),
    # Guidance & inference
    'dilip2026guide': ('guide', 'Probe Guidance'),
    'huang2026guide': ('guide', 'FMRG'),
    'shen2026flashmap': ('guide', 'FlashMap'),
    'zhang2026low': ('guide', 'ACE'),
    'inference_ye2024dinoiser': ('guide', 'DINOISER'),
    'kim2026continuous': ('guide', 'Diffinity'),
    'rekesh2026inverseconfidence': ('guide', 'INCO'),
    'li2026improving': ('guide', 'Untied Self-Cond.'),
    'vaina2024diffusion': ('guide', 'Stopping Criteria'),
    'davis2026design': ('guide', 'DoubleCat / SemiCat'),
    'shabalin2026why': ('guide', 'Why Gaussian Fails'),
    'guo2026rangeswa': ('guide', 'RangeSWA'),
    'yang2026graft': ('guide', 'GRAFT'),
    'han2026backpropagating': ('guide', 'Verifier Backprop'),
    # Reasoning, multimodal & evaluation
    'suleymanzade2026thinking': ('apps', 'Looped Flows'),
    'helbling2026flow': ('apps', 'FRM'),
    'batzolis2026multimodal': ('apps', 'Multimodal CoBit'),
    'tao2026multimodal': ('apps', 'MF-1'),
    'franca2026hacking': ('apps', 'Hacking Gen PPL'),
    'pynadath2026generative': ('apps', 'Generative Frontiers'),
    'kornhardt2026sol': ('apps', 'SOL'),
    'baek2026generative': ('apps', 'GRAM'),
    'bai2026efficient': ('apps', 'Efficient FLM Reasoning'),
    'li2026juice': ('apps', 'JUICE'),
    'caceresarroyo2026repurposing': ('apps', 'CHASE'),
    'kong2025protflow': ('apps', 'ProtFlow'),
    'meshchaninov2024diffusion': ('apps', 'DiMA'),
}

STOP = set('''a an and are as at be by can for from has have in into is it its of on or that the
their these this to was were which with while so than then them they we our also each only
both one not but more most such other same over between through using used use via all any
when where whose how what who rather instead without within same here there his her'''.split())


ACCENTS = {"'": '\u0301', '`': '\u0300', '^': '\u0302', '"': '\u0308', '~': '\u0303', 'c': '\u0327', 'v': '\u030c', '=': '\u0304'}
VENUES = [  # (pattern on journal/booktitle, short name); first match wins
    (r'ICML \d{4} Workshop', 'ICML Workshop'), (r'NeurIPS \d{4} Workshop', 'NeurIPS Workshop'),
    (r'Neural Information Processing', 'NeurIPS'), (r'International Conference on Machine Learning|\bICML\b', 'ICML'),
    (r'Learning Representations', 'ICLR'), (r'Findings of the Association for Computational Linguistics: (\w+)', r'Findings of \1'),
    (r'Empirical Methods in Natural Language Processing', 'EMNLP'),
    (r'North American', 'NAACL'), (r'European Chapter', 'EACL'), (r'Annual Meeting of the Association', 'ACL'),
    (r'Conference on Computational Linguistics', 'COLING'), (r'Transactions (?:on|in) Machine Learning Research', 'TMLR'),
    (r'AAAI', 'AAAI'), (r'Computer Vision and Pattern Recognition', 'CVPR'), (r'\(ICCV\)', 'ICCV'),
    (r'European Conference on Computer Vision', 'ECCV'), (r'arxiv', 'arXiv'),
]


def delatex(t):
    """Plain text from a bib field: accents, braces, and escapes."""
    t = re.sub(r"\\([`'^\"~=])\s*\{?\\?([A-Za-z])\}?", lambda m: m.group(2) + ACCENTS[m.group(1)], t)
    t = re.sub(r'\\([cv])\s*\{?([A-Za-z])\}?', lambda m: m.group(2) + ACCENTS[m.group(1)], t)
    t = t.replace('\\&', '&').replace('\\%', '%').replace('\\_', '_').replace('~', ' ').replace('--', '\u2013')
    t = re.sub(r'\\[a-zA-Z]+\s*', '', t).replace('{', '').replace('}', '')
    import unicodedata
    return unicodedata.normalize('NFC', re.sub(r'\s+', ' ', t)).strip()


def parse_bib(src):
    out = {}
    for chunk in re.split(r'\n(?=@)', '\n' + src):
        m = re.match(r'\s*@(\w+)\s*\{\s*([^,\s]+)\s*,(.*)', chunk, re.S)
        if not m or m.group(1).lower() in ('comment', 'string', 'preamble'):
            continue
        typ, key, body = m.groups()
        fields = {}
        for f in re.finditer(r'(\w+)\s*=\s*', body):
            i, depth, j = f.end(), 0, f.end()
            if body[i] == '{':
                for j in range(i, len(body)):
                    depth += {'{': 1, '}': -1}.get(body[j], 0)
                    if depth == 0:
                        break
                val = body[i + 1:j]
            elif body[i] == '"':
                j = body.index('"', i + 1)
                val = body[i + 1:j]
            else:
                val = re.match(r'[^,\n]*', body[i:]).group(0)
            fields.setdefault(f.group(1).lower(), val)
        names, lasts = [], []
        for a in re.split(r'\s+and\s+', re.sub(r'\s+', ' ', fields.get('author', ''))):
            a = delatex(a)
            if not a:
                continue
            if a.lower() == 'others':
                names.append('et al.')
                continue
            if ',' in a:
                last, first = [x.strip() for x in a.split(',', 1)]
                a = f'{first} {last}'
            else:  # "First Last": take as many trailing words as the citation key's surname spans
                words, stem = a.split(), re.match(r'[a-z]+', key).group(0) if not lasts else ''
                n = next((i for i in range(1, len(words)) if re.sub(r'[^a-z]', '', ''.join(words[-i:]).lower()) == stem), 1)
                last = ' '.join(words[-n:])
            names.append(a)
            lasts.append(last)
        where = fields.get('booktitle') or fields.get('journal') or ''
        venue = next((re.sub(p, v, re.search(p, where, re.I).group(0), flags=re.I) for p, v in VENUES if re.search(p, where, re.I)), delatex(where))
        ax = re.search(r'arxiv(?:\.org/abs/|[:\s]*)(\d{4}\.\d{4,5})', where + ' ' + fields.get('eprint', ''), re.I)
        title = delatex(fields.get('title', ''))
        url = (fields.get('url') or (f'https://arxiv.org/abs/{ax.group(1)}' if ax else None)
               or 'https://scholar.google.com/scholar?q=' + urllib.parse.quote_plus(title))
        year = re.search(r'\d{4}', fields.get('year', ''))
        out[key] = dict(title=title, authors=names, lasts=lasts, venue=venue, year=int(year.group(0)) if year else None,
                        url=url, mentions=[], groups=[])
    return out


CITE = re.compile(r'\\(cite[tp]?|citeauthor|citeyear|latecitep|citealp)\*?(?:\[[^\]]*\])*\{([^}]*)\}')


def survey_text(survey, refs):
    """Collect every sentence that cites a reference, with its numbered section."""
    main = open(os.path.join(survey, 'main.tex'), encoding='utf-8').read()
    inputs = re.findall(r'^[^%\n]*\\input\{Sections/([^}]+)\}', main, re.M)
    src = '\n'.join(open(os.path.join(survey, 'Sections', n + '.tex'), encoding='utf-8').read()
                    for n in inputs if not n.startswith(SKIP_INPUTS))
    src = re.sub(r'(?<!\\)%.*', '', src)
    src = re.sub(r'\\(sophia|jinwoo|ch)\{(?:[^{}]|\{[^{}]*\})*\}', '', src)  # author notes
    # Floats and display math are not prose; keep a marker so sentences stay readable.
    src = re.sub(r'\\begin\{(figure|table)\*?\}.*?\\end\{\1\*?\}', '\n\n', src, flags=re.S)
    src = re.sub(r'\\begin\{(align|equation|gather|multline)\*?\}.*?\\end\{\1\*?\}', ' \u2026 ', src, flags=re.S)
    src = re.sub(r'\\\[.*?\\\]', ' \u2026 ', src, flags=re.S)

    # Number headings and remember section labels for \ref.
    counters, labels, heads = [0, 0, 0], {}, []
    for m in re.finditer(r'\\(section|subsection|subsubsection)(\*?)\{((?:[^{}]|\{[^{}]*\})*)\}(\s*\\label\{([^}]*)\})?', src):
        lvl = ['section', 'subsection', 'subsubsection'].index(m.group(1))
        if not m.group(2):
            counters[lvl] += 1
            counters[lvl + 1:] = [0] * (2 - lvl)
        num = '.'.join(str(c) for c in counters[:lvl + 1]) if not m.group(2) else ''
        if m.group(5):
            labels[m.group(5)] = num
        heads.append((m.start(), lvl, num, delatex(m.group(3))))
    for m in re.finditer(r'\\label\{([^}]*)\}', src):  # labels placed after the heading line
        if m.group(1) not in labels:
            prev = [h for h in heads if h[0] < m.start()]
            if prev and m.group(1).startswith(('sec', 'subsec', 'subsubsec')):
                labels[m.group(1)] = prev[-1][2]

    def clean(t, groups):
        math = []
        t = re.sub(r'\$[^$]+\$', lambda m: (math.append(m.group(0)), f'\x01{len(math) - 1}\x01')[1], t)

        def cite(m):
            keys = [k.strip() for k in m.group(2).split(',') if k.strip()]
            groups.append(keys)
            lead = ''
            if m.group(1) in ('citet', 'citeauthor') and keys and keys[0] in refs:
                la = [x for x in refs[keys[0]]['lasts']]
                many = len(la) > 2 or 'et al.' in refs[keys[0]]['authors']
                lead = ' ' + (la[0] + ' et al.' if many else ' and '.join(la)) if la else ''
            # The marker goes first so a sentence split after "al." cannot separate it from the name.
            return f'\x00{len(groups) - 1}\x00{lead}'
        t = CITE.sub(cite, t)
        t = re.sub(r'(Sections?|Figures?|Tables?|Eqs?\.?)~\\ref\{([^}]*)\}(--\\ref\{([^}]*)\})?',
                   lambda m: m.group(1) + ' ' + labels.get(m.group(2), '') + ('\u2013' + labels.get(m.group(4), '') if m.group(3) else ''), t)
        t = re.sub(r'~?\\(eq)?ref\{[^}]*\}', '', t)
        t = re.sub(r'\\label\{[^}]*\}', '', t)
        for _ in range(3):
            t = re.sub(r'\\(?:textbf|emph|textit|texttt|textsc|textrm|mbox|text)\{((?:[^{}]|\{[^{}]*\})*)\}', r'\1', t)
        t = t.replace('---', '\u2014').replace('--', '\u2013').replace('``', '\u201c').replace("''", '\u201d')
        t = delatex(t.replace('~', ' '))
        t = re.sub(r'\s+([,.;:)])', r'\1', t)
        return re.sub(r'\x01(\d+)\x01', lambda m: math[int(m.group(1))], t)

    for para in re.split(r'\n\s*\n', src):
        if not CITE.search(para):
            continue
        at = src.find(para)
        before = [h for h in heads if h[0] <= at]
        top = next((h for h in reversed(before) if h[1] == 0), None)
        sub = before[-1] if before else None
        part = f'{top[2]} {top[3]}'.strip() if top else ''
        sec_title = f'{sub[2]} {sub[3]}'.strip() if sub and sub is not top else ''
        body = re.sub(r'\\(section|subsection|subsubsection|paragraph)\*?\{(?:[^{}]|\{[^{}]*\})*\}', ' ', para)
        groups = []
        text = clean(re.sub(r'\s+', ' ', body), groups)
        for sent in re.split(r'(?<=[.!?])\s+(?=[A-Z\x00])', text):
            plain = re.sub(r'\s*\x00\d+\x00', '', sent).strip()
            plain = re.sub(r'\(\s*\)|\s+(?=[,.;:])', '', plain).strip()
            for i in map(int, re.findall(r'\x00(\d+)\x00', sent)):
                for k in groups[i]:
                    if k not in refs or not plain:
                        continue
                    if not any(x['text'] == plain for x in refs[k]['mentions']):
                        refs[k]['mentions'].append(dict(part=part, secTitle=sec_title, text=plain))
                    refs[k]['groups'].append(groups[i])
    return refs


def tokens(text):
    text = re.sub(r'\$[^$]*\$', ' ', text.lower())
    return [w for w in re.findall(r'[a-z][a-z\-]+', text) if w not in STOP and len(w) > 2]


def main():
    refs = parse_bib(open(os.path.join(SURVEY, 'citation_final.bib'), encoding='utf-8').read())
    meta = json.load(open(os.path.join(HERE, 'paper_meta.json'), encoding='utf-8'))
    no_overview = [k for k in PAPERS if not meta.get(k, {}).get('overview')]
    assert not no_overview, f'no overview in paper_meta.json: {no_overview}'
    missing = [k for k in PAPERS if k not in refs]
    assert not missing, f'not in {SURVEY}/citation_final.bib: {missing}'
    refs = survey_text(SURVEY, refs)
    uncited = [k for k in PAPERS if not refs[k]['mentions']]
    assert not uncited, f'not cited in the survey text: {uncited}'
    keys = list(PAPERS)
    cat_ids = [c[0] for c in CATS]

    # TF-IDF over the title (weighted up) and every sentence citing the paper.
    docs = []
    for k in keys:
        r = refs[k]
        docs.append(Counter(tokens(r['title']) * 3 + [w for x in r['mentions'] for w in tokens(x['text'])]))
    df = Counter(w for d in docs for w in d)
    vocab = sorted(w for w, c in df.items() if 2 <= c <= 0.5 * len(docs))
    vi = {w: i for i, w in enumerate(vocab)}
    X = np.zeros((len(keys), len(vocab)))
    for i, d in enumerate(docs):
        for w, c in d.items():
            if w in vi:
                X[i, vi[w]] = (1 + math.log(c)) * math.log(len(docs) / df[w])
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9

    radius = np.array([4.5 + 1.25 * math.sqrt(len(refs[k]['mentions'])) for k in keys])
    pos = np.zeros((len(keys), 2))
    center = {}
    for cid, _, c in CATS:
        idx = [i for i, k in enumerate(keys) if PAPERS[k][0] == cid]
        center[cid] = np.array(c, float)
        Y = X[idx] - X[idx].mean(0)
        with np.errstate(all='ignore'):  # spurious BLAS warnings on some numpy builds
            _, _, vt = np.linalg.svd(Y, full_matrices=False)
            P = Y @ vt[:2].T
        P /= np.abs(P).max(0) + 1e-9
        spread = 26 * math.sqrt(len(idx))
        pos[idx] = c + P * spread * np.array([1.25, 0.85])

    # Pull co-cited papers in other clusters slightly toward each other, then relax overlaps.
    kidx = {k: i for i, k in enumerate(keys)}
    co = Counter()
    for k in keys:
        for g in refs[k]['groups']:
            for j in g:
                if j in kidx and j != k:
                    co[tuple(sorted((k, j)))] += 1
    anchor = pos.copy()
    gap = 9.0  # room for the label underneath large nodes
    for step in range(400):
        f = 0.08 * (anchor - pos)
        for (a, b), w in co.items():
            i, j = kidx[a], kidx[b]
            if PAPERS[a][0] != PAPERS[b][0]:
                d = pos[j] - pos[i]
                f[i] += 0.0006 * w * d
                f[j] -= 0.0006 * w * d
        d = pos[:, None, :] - pos[None, :, :]
        dist = np.linalg.norm(d, axis=2) + np.eye(len(keys))
        need = 1.3 * (radius[:, None] + radius[None, :]) + gap  # pointed shapes reach ~1.35 r
        push = np.clip(need - dist, 0, None) / dist
        np.fill_diagonal(push, 0)
        f += 0.5 * (d * push[:, :, None]).sum(1)
        pos += f
    pos = np.clip(pos, 20, [1040, 740])

    papers = []
    for i, k in enumerate(keys):
        r = refs[k]
        info = meta[k]
        arxiv = info.get('arxiv')
        cat, short = PAPERS[k]
        surname = (r['authors'][0].split()[-1] if r['authors'] else '').lower()

        def score(m):
            t = m['text'].lower()
            return (short.lower().split(' /')[0] in t) * 2 + (surname in t)
        mentions = sorted(r['mentions'], key=score, reverse=True)[:4]
        related = sorted(((w, b if a == k else a) for (a, b), w in co.items() if k in (a, b)), reverse=True)
        papers.append(dict(
            id=k, short=short, cat=cat, title=r['title'],
            authors=r['authors'], venue=r['venue'], year=r['year'],
            url=f'https://arxiv.org/abs/{arxiv}' if arxiv else r['url'], arxiv=arxiv, code=info.get('code'), overview=info['overview'],
            n=len(r['mentions']), x=round(float(pos[i, 0]), 1), y=round(float(pos[i, 1]), 1),
            r=round(float(radius[i]), 2), mentions=mentions,
            related=[j for _, j in related[:8]]))

    data = dict(cats=[dict(id=c, label=l) for c, l, _ in CATS], papers=papers)
    with open(os.path.join(HERE, 'data.js'), 'w', encoding='utf-8') as fh:
        fh.write('// Generated by build_map_data.py. Do not edit by hand.\n')
        fh.write('window.CLM_MAP = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
    # Version the page's local assets by content so browsers drop stale copies.
    import hashlib
    page = os.path.join(HERE, 'index.html')
    src = open(page, encoding='utf-8').read()
    for name in ('data.js', 'map.js', 'map.css'):
        digest = hashlib.sha1(open(os.path.join(HERE, name), 'rb').read()).hexdigest()[:10]
        src = re.sub(r'(["\'])' + re.escape(name) + r'(\?v=[0-9a-f]+)?\1', lambda m: f'{m.group(1)}{name}?v={digest}{m.group(1)}', src)
    open(page, 'w', encoding='utf-8').write(src)
    print(f'{len(papers)} papers, {len(co)} co-citation pairs')


if __name__ == '__main__':
    main()
