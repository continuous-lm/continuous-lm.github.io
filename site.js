(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

  let toastTimer;
  function toast(message) {
    $('#toast').textContent = message;
    $('#toast').classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $('#toast').classList.remove('show'), 3000);
  }
  async function copy(text, confirmation) {
    try {
      await navigator.clipboard.writeText(text);
      toast(confirmation);
    } catch {
      const field = document.createElement('textarea');
      field.value = text;
      field.style.cssText = 'position:fixed;left:-9999px';
      document.body.append(field);
      field.select();
      const copied = document.execCommand('copy');
      field.remove();
      toast(copied ? confirmation : 'Clipboard unavailable. Select and copy the citation.');
    }
  }
  $('#copy-bibtex').addEventListener('click', () => copy($('#bibtex-code').textContent, 'BibTeX copied'));

  // The map preview loops on its own, unless the reader asked for less motion.
  const mapVideo = $('.map-preview video');
  if (mapVideo && reducedMotion.matches) { mapVideo.removeAttribute('autoplay'); mapVideo.pause(); }

  // Resources that are not public yet explain themselves instead of jumping to the top.
  for (const link of $$('[data-placeholder]')) {
    link.addEventListener('click', event => {
      event.preventDefault();
      toast(link.dataset.placeholder);
    });
  }

  // Track section geometry so the rail follows the reader.
  const contents = $('#contents');
  const contentsToggle = $('.contents-toggle', contents);
  const contentsLinks = $$('.contents-list a', contents);
  const sections = contentsLinks.map(link => $(link.getAttribute('href')));
  const compactContents = matchMedia('(max-width: 1279px)');
  let contentsFrame;

  function closeContents() {
    contents.classList.remove('is-open');
    contentsToggle.setAttribute('aria-expanded', 'false');
  }
  function updateContents() {
    contentsFrame = null;
    const visible = scrollY > 120;
    contents.classList.toggle('is-visible', visible);
    contents.inert = !visible;
    if (!visible) closeContents();
    const readingLine = Math.min(innerHeight * .28, 220);
    let active = sections[0];
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= readingLine) active = section;
    }
    // A short final section still becomes current when the reader reaches the end.
    if (scrollY + innerHeight >= document.documentElement.scrollHeight - 4) active = sections.at(-1);
    for (const link of contentsLinks) {
      if (link.hash === '#' + active.id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
    $('.contents-current', contents).textContent = contentsLinks[sections.indexOf(active)].textContent;
  }
  function scheduleContents() {
    if (contentsFrame == null) contentsFrame = requestAnimationFrame(updateContents);
  }
  contentsToggle.addEventListener('click', () => {
    const open = contents.classList.toggle('is-open');
    contentsToggle.setAttribute('aria-expanded', String(open));
  });
  for (const link of [...contentsLinks, ...$$('.project-contents a, a[href^="#"]:not([data-placeholder])')]) {
    link.addEventListener('click', event => {
      // Preserve normal new-tab and modified-click behavior on these real anchors.
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const section = link.hash && $(link.hash);
      if (!section) return;
      event.preventDefault();
      history.pushState(null, '', link.hash);
      closeContents();
      const heading = section.querySelector('h1, h2, h3');
      heading.setAttribute('tabindex', '-1');
      heading.focus({preventScroll: true});
      section.scrollIntoView({behavior: reducedMotion.matches ? 'instant' : 'smooth'});
      scheduleContents();
    });
  }
  document.addEventListener('click', event => {
    if (!contents.contains(event.target)) closeContents();
  });
  contents.addEventListener('keydown', event => {
    if (event.key === 'Escape' && contents.classList.contains('is-open')) {
      closeContents();
      contentsToggle.focus();
    }
  });
  contents.addEventListener('focusout', event => {
    if (!contents.contains(event.relatedTarget)) closeContents();
  });
  compactContents.addEventListener('change', () => {closeContents(); scheduleContents();});
  window.addEventListener('scroll', scheduleContents, {passive: true});
  window.addEventListener('resize', scheduleContents);
  window.addEventListener('hashchange', scheduleContents);
  window.addEventListener('pageshow', scheduleContents);
  new ResizeObserver(scheduleContents).observe($('#main'));
  updateContents();
})();
