(() => {
  const box = document.querySelector('[data-denoise]');
  if (!box) return;
  const text = box.querySelector('.denoise-text');
  const controls = box.querySelector('.denoise-controls');
  const slider = box.querySelector('input[type="range"]');
  const readout = box.querySelector('output');
  const play = box.querySelector('.denoise-play');
  const modes = [...box.querySelectorAll('input[name="denoise-mode"]')];
  const sentence = text.textContent;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');

  // Words that overlap each position in continuous mode, before the final word resolves.
  const VOCABULARY = 'a of in to on by as we the for can are our new its each from with that this over than both most word time step data form text large small model token given learn state paths early score signal vector random sample neural method search sequence sampling training gradient semantic embedding structure parameter inference iterative generative discrete distribution probability conditional computation transformations approximations interpretations representation'.split(' ');
  const FLOOR = .24;  // Opacity of every candidate at t = 0.

  // A small seeded generator, so the same word gets the same schedule on every render.
  const hash = n => {
    const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
    return x - Math.floor(x);
  };

  const words = sentence.split(' ');
  const wordOrder = words.map((_, i) => i).sort((a, b) => hash(a + 40) - hash(b + 40));
  const wordRank = words.map((_, i) => wordOrder.indexOf(i) / words.length);
  const chars = [];
  const flow = [];
  let built = null;

  // Candidates close in length to the final word, so they overlap it without spilling far past it.
  function candidates(word, w) {
    const bare = word.replace(/\W/g, '').toLowerCase();
    return VOCABULARY.filter(c => c !== bare)
      .map((c, i) => [Math.abs(c.length - bare.length) + 3 * hash(w * 31 + i), c])
      .sort((a, b) => a[0] - b[0])
      .slice(0, 3)
      .map(pair => pair[1]);
  }

  function flowWord(word, w) {
    const span = document.createElement('span');
    span.className = 'dn-word';
    const target = document.createElement('span');
    target.className = 'dn-target';
    target.textContent = word;
    const ghosts = candidates(word, w).map(c => {
      const ghost = document.createElement('span');
      ghost.className = 'dn-ghost';
      ghost.textContent = c;
      return ghost;
    });
    span.append(target, ...ghosts);
    flow.push({target, ghosts, start: .08 + .45 * wordRank[w]});
    return span;
  }

  // Every character keeps its own width, so the line breaks stay put while the text resolves.
  function charWord(word, w) {
    const span = document.createElement('span');
    span.className = 'dn-word';
    for (const ch of word) {
      const cell = document.createElement('span');
      cell.className = 'dn-ch';
      const clean = document.createElement('span');
      clean.className = 'dn-clean';
      clean.textContent = ch;
      const noise = document.createElement('span');
      noise.className = 'dn-noise';
      noise.textContent = '▒';
      noise.hidden = true;
      cell.append(clean, noise);
      span.append(cell);
      chars.push({cell, noise, word: w});
    }
    return span;
  }

  function build(m) {
    chars.length = 0;
    flow.length = 0;
    const frag = document.createDocumentFragment();
    words.forEach((word, w) => {
      frag.append(m === 'continuous' ? flowWord(word, w) : charWord(word, w));
      if (w < words.length - 1) frag.append(' ');
    });
    text.setAttribute('aria-label', sentence);
    text.replaceChildren(frag);
    // Assistive tech reads the sentence from the label, not the moving words.
    for (const child of text.children) child.setAttribute('aria-hidden', 'true');
    built = m;
  }

  const mode = () => modes.find(m => m.checked).value;

  function paint(t) {
    const m = mode();
    readout.textContent = t.toFixed(2);
    if (t >= 1 && m !== 'continuous') {
      text.textContent = sentence;
      built = null;
      return;
    }
    if (built !== m) build(m);
    if (m === 'continuous') {
      for (const {target, ghosts, start} of flow) {
        const x = Math.min(1, Math.max(0, (t - start) / .42));
        const w = x * x * (3 - 2 * x);
        target.style.opacity = (FLOOR + (1 - FLOOR) * w).toFixed(3);
        for (const ghost of ghosts) {
          ghost.style.opacity = (FLOOR * (1 - w)).toFixed(3);
          ghost.hidden = w >= 1;  // Keeps finished text clean to select and copy.
        }
      }
      return;
    }
    for (const c of chars) {
      let state;
      if (m === 'masked') state = t >= .1 + .85 * wordRank[c.word] ? 'clean' : 'mask';
      else state = t >= c.word / words.length ? 'clean' : 'blank';
      c.cell.classList.toggle('is-noisy', state === 'mask');
      c.cell.classList.toggle('is-mask', state === 'mask');
      c.cell.classList.toggle('is-blank', state === 'blank');
      c.noise.hidden = state !== 'mask';
    }
  }

  let raf = 0;
  function stop() {
    cancelAnimationFrame(raf);
    raf = 0;
  }
  function run() {
    stop();
    if (reduced.matches) {
      slider.value = 1;
      paint(1);
      return;
    }
    const start = performance.now();
    const step = now => {
      const t = Math.min(1, (now - start) / 4000);
      slider.value = t;
      paint(t);
      raf = t < 1 ? requestAnimationFrame(step) : 0;
    };
    raf = requestAnimationFrame(step);
  }

  controls.hidden = false;
  slider.addEventListener('input', () => { stop(); paint(+slider.value); });
  play.addEventListener('click', run);
  for (const m of modes) m.addEventListener('change', run);

  // Generate the sentence once, the first time the reader reaches it.
  if ('IntersectionObserver' in window && !reduced.matches) {
    const seen = new IntersectionObserver(entries => {
      if (!entries.some(entry => entry.isIntersecting)) return;
      seen.disconnect();
      run();
    }, {threshold: .6});
    seen.observe(text);
  }
})();
