/**
 * ReFind hero text reveal — lightweight character stagger (Antigravity TypedHeader spirit)
 * No GSAP required. Plays once per page load. Respects prefers-reduced-motion.
 */
(function (global) {
  'use strict';

  function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function splitIntoChars(el) {
    var text = el.textContent;
    el.setAttribute('aria-label', text.trim());
    el.textContent = '';
    el.classList.add('rf-reveal');

    var frag = document.createDocumentFragment();
    for (var i = 0; i < text.length; i++) {
      var ch = text[i];
      if (ch === '\n') {
        frag.appendChild(document.createElement('br'));
        continue;
      }
      var span = document.createElement('span');
      span.className = 'rf-reveal-char';
      span.textContent = ch === ' ' ? '\u00a0' : ch;
      frag.appendChild(span);
    }
    var cursor = document.createElement('span');
    cursor.className = 'rf-reveal-cursor';
    cursor.setAttribute('aria-hidden', 'true');
    frag.appendChild(cursor);
    el.appendChild(frag);
    return el.querySelectorAll('.rf-reveal-char');
  }

  function reveal(el, options) {
    options = options || {};
    if (!el || el.dataset.revealed === '1') return;
    el.dataset.revealed = '1';

    if (prefersReducedMotion()) {
      el.classList.add('rf-reveal', 'is-done');
      return;
    }

    var chars = splitIntoChars(el);
    var delay = options.delay != null ? options.delay : 180;
    var stagger = options.stagger != null ? options.stagger : 28;

    chars.forEach(function (char, index) {
      char.style.transition =
        'opacity 280ms cubic-bezier(0.16, 1, 0.3, 1), transform 280ms cubic-bezier(0.16, 1, 0.3, 1)';
      char.style.transitionDelay = delay + index * stagger + 'ms';
      requestAnimationFrame(function () {
        char.style.opacity = '1';
        char.style.transform = 'none';
      });
    });

    var total = delay + chars.length * stagger + 320;
    setTimeout(function () {
      el.classList.add('is-done');
    }, total);
  }

  function init(root) {
    var scope = root || document;
    scope.querySelectorAll('[data-text-reveal]').forEach(function (el) {
      var delay = el.getAttribute('data-reveal-delay');
      var stagger = el.getAttribute('data-reveal-stagger');
      reveal(el, {
        delay: delay != null ? Number(delay) : undefined,
        stagger: stagger != null ? Number(stagger) : undefined,
      });
    });
  }

  global.ReFindTextReveal = { init: init, reveal: reveal };
})(window);
