/**
 * ReFind ambient particles — lightweight 2D canvas (green organic motion)
 * Inspired by Antigravity particle systems, without Three.js weight.
 * Pauses when offscreen / hidden tab. Reduced density on mobile. Static fallback.
 */
(function (global) {
  'use strict';

  function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function isFinePointer() {
    return window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  }

  function createAmbient(canvas) {
    if (!canvas || prefersReducedMotion()) return null;

    var ctx = canvas.getContext('2d');
    if (!ctx) return null;

    var particles = [];
    var raf = 0;
    var running = false;
    var visible = true;
    var mouse = { x: 0.5, y: 0.5, active: false };
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var hero = canvas.closest('.hero') || canvas.parentElement;

    function density() {
      var w = hero.clientWidth || 800;
      if (w < 600) return 18;
      if (w < 1024) return 28;
      return 42;
    }

    function resize() {
      var rect = hero.getBoundingClientRect();
      var w = Math.max(1, Math.floor(rect.width));
      var h = Math.max(1, Math.floor(rect.height));
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      seed(w, h);
    }

    function seed(w, h) {
      var count = density();
      particles = [];
      for (var i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * w,
          y: Math.random() * h,
          r: 1.2 + Math.random() * 2.8,
          vx: (Math.random() - 0.5) * 0.25,
          vy: -0.15 - Math.random() * 0.35,
          a: 0.15 + Math.random() * 0.35,
          leaf: Math.random() > 0.72,
          rot: Math.random() * Math.PI * 2,
          vr: (Math.random() - 0.5) * 0.02,
        });
      }
    }

    function color(alpha) {
      var dark = document.documentElement.getAttribute('data-theme') === 'dark';
      return dark
        ? 'rgba(61, 214, 140,' + alpha + ')'
        : 'rgba(8, 123, 68,' + alpha + ')';
    }

    function drawLeaf(p) {
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.beginPath();
      ctx.ellipse(0, 0, p.r * 1.8, p.r * 0.9, 0, 0, Math.PI * 2);
      ctx.fillStyle = color(p.a * 0.85);
      ctx.fill();
      ctx.restore();
    }

    function frame() {
      if (!running || !visible) return;
      var w = canvas.width / dpr;
      var h = canvas.height / dpr;
      ctx.clearRect(0, 0, w, h);

      for (var i = 0; i < particles.length; i++) {
        var p = particles[i];
        if (mouse.active && isFinePointer()) {
          var dx = p.x - mouse.x * w;
          var dy = p.y - mouse.y * h;
          var dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist < 120) {
            var force = (120 - dist) / 120;
            p.vx += (dx / dist) * force * 0.08;
            p.vy += (dy / dist) * force * 0.08;
          }
        }
        p.vx *= 0.98;
        p.vy *= 0.98;
        p.x += p.vx;
        p.y += p.vy;
        p.rot += p.vr;

        if (p.y < -10) p.y = h + 10;
        if (p.y > h + 10) p.y = -10;
        if (p.x < -10) p.x = w + 10;
        if (p.x > w + 10) p.x = -10;

        if (p.leaf) {
          drawLeaf(p);
        } else {
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
          ctx.fillStyle = color(p.a);
          ctx.fill();
        }
      }
      raf = requestAnimationFrame(frame);
    }

    function start() {
      if (running) return;
      running = true;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(frame);
    }

    function stop() {
      running = false;
      cancelAnimationFrame(raf);
    }

    function onMove(e) {
      var rect = hero.getBoundingClientRect();
      mouse.x = (e.clientX - rect.left) / rect.width;
      mouse.y = (e.clientY - rect.top) / rect.height;
      mouse.active = true;
    }

    function onLeave() {
      mouse.active = false;
    }

    var io = null;
    if ('IntersectionObserver' in window) {
      io = new IntersectionObserver(
        function (entries) {
          visible = entries[0] && entries[0].isIntersecting;
          if (visible) start();
          else stop();
        },
        { threshold: 0.05 }
      );
      io.observe(hero);
    }

    function onVisibility() {
      if (document.hidden) stop();
      else if (visible) start();
    }

    resize();
    start();
    window.addEventListener('resize', resize, { passive: true });
    document.addEventListener('visibilitychange', onVisibility);
    if (isFinePointer()) {
      hero.addEventListener('pointermove', onMove, { passive: true });
      hero.addEventListener('pointerleave', onLeave);
    }

    return {
      destroy: function () {
        stop();
        window.removeEventListener('resize', resize);
        document.removeEventListener('visibilitychange', onVisibility);
        hero.removeEventListener('pointermove', onMove);
        hero.removeEventListener('pointerleave', onLeave);
        if (io) io.disconnect();
      },
    };
  }

  function init(root) {
    var scope = root || document;
    scope.querySelectorAll('[data-ambient]').forEach(function (canvas) {
      if (canvas._rfAmbient) return;
      canvas._rfAmbient = createAmbient(canvas);
    });
  }

  global.ReFindAmbient = { init: init };
})(window);
