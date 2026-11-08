"""Render the landing page's preview images from the survey sources.

Writes the overview figures, Figure 1, and the paper cover into assets/.
Figures are saved as lossless WebP, since lossy WebP blurs thin colored lines and text.
Needs PyMuPDF and Pillow, which only this script uses.

    python3 scripts/render_figures.py [path/to/clm_survey_vN] [path/to/clm_survey_cover.png]
"""
import io, os, sys

import fitz
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURVEY = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '..', '..', 'clm_survey_v9'))
COVER = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, '..', '..', 'clm_survey_cover.png'))
FIGURES = ['statespace_overview', 'continuous_inference_overview', 'few_step_overview', 'applications_overview']
OUT = os.path.join(ROOT, 'assets', 'figures')

for name in FIGURES:
    page = fitz.open(os.path.join(SURVEY, 'Figures', name + '.pdf'))[0]
    # Well above display size, so the previews stay sharp on high-density screens.
    pix = page.get_pixmap(dpi=320, alpha=False)
    Image.open(io.BytesIO(pix.tobytes('png'))).save(os.path.join(OUT, name + '.webp'), lossless=True, method=6)

timeline = Image.open(os.path.join(SURVEY, 'Figures', 'clm-timeline.png')).convert('RGBA')
flat = Image.new('RGB', timeline.size, 'white')
flat.paste(timeline, mask=timeline.getchannel('A'))
flat.save(os.path.join(OUT, 'timeline_overview.webp'), lossless=True, method=6)

cover = Image.open(COVER).convert('RGB')
cover.resize((680, 880), Image.LANCZOS).save(os.path.join(ROOT, 'assets', 'previews', 'paper-cover.png'), optimize=True)
