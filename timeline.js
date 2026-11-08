(() => {
  const svg = document.querySelector('svg.tl');
  if (!svg) return;
  const $$ = (selector, root = svg) => [...root.querySelectorAll(selector)];
  const scroller = svg.closest('.tl-scroll');
  const tip = scroller.querySelector('.tl-tip');
  const cards = $$('.tl-card');
  const arrows = $$('.tl-arrow');
  const legend = $$('.tl-legend');
  const S = 40;  // px per TikZ cm, as in build_timeline.py

  // Once the Computer Modern fonts load, shrink long labels to the card width
  // (TikZ's \tvFit does the same) and size the year and month chips to their text.
  function fitText() {
    for (const card of cards) {
      const label = card.querySelector('.tl-label');
      const box = card.querySelector('.tl-box');
      label.removeAttribute('transform');
      const width = label.getBBox().width;
      const limit = 1.35 * S;
      if (width > limit) {
        const k = limit / width;
        const cx = +box.getAttribute('x') + +box.getAttribute('width') / 2;
        const cy = +box.getAttribute('y') + +box.getAttribute('height') / 2;
        label.setAttribute('transform', `translate(${cx * (1 - k)} ${cy * (1 - k)}) scale(${k})`);
      }
    }
    for (const [selector, pad] of [['.tl-year', 5.6], ['.tl-month', 2.8]]) {
      for (const chip of $$(selector)) {
        const text = chip.querySelector('text');
        const rect = chip.querySelector('rect');
        const w = text.getBBox().width + 2 * pad;
        rect.setAttribute('x', +text.getAttribute('x') - w / 2);
        rect.setAttribute('width', w);
      }
    }
  }
  (document.fonts ? document.fonts.ready : Promise.resolve()).then(fitText);

  // Tooltips.
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  function showTip(card) {
    const d = card.dataset;
    const tags = [];
    if (card.classList.contains('has-few')) tags.push('<span><i class="is-few"></i>Few-step / flow maps</span>');
    if (card.classList.contains('has-guide')) tags.push('<span><i class="is-guide"></i>Guidance</span>');
    const links = [];
    if (d.arxiv) {
      links.push(`<a href="https://arxiv.org/abs/${esc(d.arxiv)}" target="_blank" rel="noopener">arXiv ↗</a>`);
      links.push(`<a href="https://www.alphaxiv.org/abs/${esc(d.arxiv)}" target="_blank" rel="noopener">alphaXiv ↗</a>`);
    } else if (card.getAttribute('href')) {
      links.push(`<a href="${esc(card.getAttribute('href'))}" target="_blank" rel="noopener">Paper ↗</a>`);
    }
    if (d.code) links.push(`<a href="${esc(d.code)}" target="_blank" rel="noopener">Code ↗</a>`);
    const meta = [d.authors, d.venue].filter(Boolean).join(' · ');
    tip.innerHTML =
      `<strong>${esc(d.name)}</strong>` +
      (d.title ? `<div class="tip-title">${esc(d.title)}</div>` : '') +
      (meta ? `<div class="tip-meta">${esc(meta)}</div>` : '') +
      `<div class="tip-meta">${esc(d.date)} · ${esc(d.family)}</div>` +
      (tags.length ? `<div class="tip-tags">${tags.join('')}</div>` : '') +
      (links.length ? `<div class="tip-links">${links.join('')}</div>` : '');
    tip.style.setProperty('--tip-line', getComputedStyle(card).getPropertyValue('--tl-line'));
    tip.hidden = false;
    const box = card.querySelector('.tl-box').getBoundingClientRect();
    const host = scroller.getBoundingClientRect();
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    let left = box.left - host.left + scroller.scrollLeft + box.width / 2 - tw / 2;
    left = Math.max(scroller.scrollLeft + 4, Math.min(left, scroller.scrollLeft + host.width - tw - 4));
    const below = box.bottom - host.top + 8;
    const above = box.top - host.top - th - 8;
    tip.style.left = `${left}px`;
    tip.style.top = `${above >= 0 && box.top - host.top > host.height / 2 ? above : below}px`;
  }
  function hideTip() { clearTimeout(hideTimer); tip.hidden = true; }
  // The tooltip holds links, so it stays up while the pointer crosses the gap to reach it.
  let hideTimer, hovered = null;
  function leaveSoon() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      hideTip();
      if (hovered) { link(hovered, false); hovered = null; }
    }, 180);
  }
  tip.addEventListener('pointerenter', () => clearTimeout(hideTimer));
  tip.addEventListener('pointerleave', e => { if (e.pointerType !== 'touch') leaveSoon(); });

  // Arrows and the papers at their ends light up with the hovered paper.
  function link(card, on) {
    const id = card.id.replace(/^tl-/, '');
    svg.classList.toggle('is-hovering', on);
    for (const arrow of arrows) {
      const hit = arrow.dataset.from === id || arrow.dataset.to === id;
      arrow.classList.toggle('is-linked', on && hit);
      if (!hit) continue;
      const other = svg.getElementById('tl-' + (arrow.dataset.from === id ? arrow.dataset.to : arrow.dataset.from));
      other?.classList.toggle('is-linked', on);
    }
  }

  let armed = null;  // on touch, the first tap shows details and links, and the second opens the paper
  for (const card of cards) {
    card.addEventListener('pointerenter', e => {
      if (e.pointerType === 'touch') return;
      clearTimeout(hideTimer);
      if (hovered && hovered !== card) link(hovered, false);
      hovered = card;
      showTip(card);
      link(card, true);
    });
    card.addEventListener('pointerleave', e => { if (e.pointerType !== 'touch') leaveSoon(); });
    card.addEventListener('focus', () => { showTip(card); link(card, true); });
    card.addEventListener('blur', e => {
      if (tip.contains(e.relatedTarget)) return;
      hideTip();
      link(card, false);
    });
    card.addEventListener('pointerdown', e => { card.dataset.touch = e.pointerType === 'touch' ? '1' : ''; });
    card.addEventListener('click', e => {
      if (card.dataset.touch !== '1' || armed === card) return;
      e.preventDefault();
      if (armed) { armed.classList.remove('is-active'); link(armed, false); }
      armed = card;
      card.classList.add('is-active');
      showTip(card);
      link(card, true);
    });
  }
  document.addEventListener('pointerdown', e => {
    if (armed && !armed.contains(e.target) && !tip.contains(e.target)) { armed.classList.remove('is-active'); link(armed, false); hideTip(); armed = null; }
  });
  scroller.addEventListener('scroll', hideTip, {passive: true});

  // Legend entries highlight one family or one kind of adaptation at a time.
  let filter = null;
  function setFilter(next) {
    filter = filter === next ? null : next;
    svg.classList.toggle('is-filtering', !!filter);
    for (const card of cards) card.classList.toggle('is-match', !!filter && card.classList.contains(filter));
    for (const entry of legend) entry.setAttribute('aria-pressed', String(entry.dataset.filter === filter));
  }
  for (const entry of legend) {
    entry.addEventListener('click', () => setFilter(entry.dataset.filter));
    entry.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setFilter(entry.dataset.filter); }
    });
  }
  svg.addEventListener('keydown', e => { if (e.key === 'Escape' && filter) setFilter(filter); });
})();
