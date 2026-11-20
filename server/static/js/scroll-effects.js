/**
 * ReFind scroll effects — IntersectionObserver section/card reveals
 */
(function (global) {
  'use strict';

  function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function markVisible(el) {
    el.classList.add('is-visible');
  }

  function init(root) {
    var scope = root || document;
    var nodes = scope.querySelectorAll('.rf-animate, .rf-animate-scale, [data-animate]');
    if (!nodes.length) return;

    nodes.forEach(function (el) {
      if (el.hasAttribute('data-animate') && !el.classList.contains('rf-animate')) {
        el.classList.add('rf-animate');
      }
    });

    if (prefersReducedMotion() || !('IntersectionObserver' in window)) {
      nodes.forEach(markVisible);
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          markVisible(entry.target);
          observer.unobserve(entry.target);
        });
      },
      { root: null, rootMargin: '0px 0px -8% 0px', threshold: 0.12 }
    );

    nodes.forEach(function (el, index) {
      if (el.parentElement && el.parentElement.classList.contains('rf-stagger')) {
        el.style.setProperty('--stagger-index', String(Math.min(index, 12)));
      }
      observer.observe(el);
    });
  }

  global.ReFindScroll = { init: init };
})(window);
