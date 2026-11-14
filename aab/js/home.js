/* Atlas After Blue — home page interactions.
   Loaded after common.js. Does NOT touch the menu toggle or the image
   viewer logic, which stay in common.js. */
(function () {
  'use strict';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var root = document.documentElement;
  var hero = document.getElementById('hero');
  var header = document.getElementById('site-header');

  /* 1. Header: transparent over hero, solid after scrolling */
  function onScroll() {
    var y = window.scrollY || 0;
    if (header) {
      header.classList.toggle('is-over-hero', y < 24);
      header.classList.toggle('is-scrolled', y >= 24);
    }
    if (hero && !reduce && y < window.innerHeight) {
      hero.style.setProperty('--sy', (y * 0.12).toFixed(1));
    }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* 2. Hero: mouse parallax + cursor glow */
  if (hero && !reduce && window.matchMedia('(pointer: fine)').matches) {
    hero.addEventListener('pointermove', function (e) {
      var r = hero.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width;
      var y = (e.clientY - r.top) / r.height;
      hero.style.setProperty('--mx', (x * 2 - 1).toFixed(3));
      hero.style.setProperty('--my', (y * 2 - 1).toFixed(3));
      hero.style.setProperty('--px', (x * 100).toFixed(1) + '%');
      hero.style.setProperty('--py', (y * 100).toFixed(1) + '%');
    });
    hero.addEventListener('pointerleave', function () {
      hero.style.setProperty('--mx', 0);
      hero.style.setProperty('--my', 0);
    });
  }

  /* 3. Scroll reveal */
  var reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add('in'); });
  }

  /* 4. Count-up for key figures (final value is already in the HTML) */
  var counts = document.querySelectorAll('.count[data-to]');
  function runCount(el) {
    var to = parseFloat(el.dataset.to);
    var dec = parseInt(el.dataset.dec || '0', 10);
    var dur = 1300, t0 = null;
    function step(t) {
      if (t0 === null) t0 = t;
      var p = Math.min((t - t0) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = (to * eased).toFixed(dec);
      if (p < 1) requestAnimationFrame(step); else el.textContent = to.toFixed(dec);
    }
    requestAnimationFrame(step);
  }
  if ('IntersectionObserver' in window && !reduce) {
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { runCount(en.target); cio.unobserve(en.target); }
      });
    }, { threshold: 0.6 });
    counts.forEach(function (el) { cio.observe(el); });
  }

  /* 5. Metric cards: glow follows the cursor */
  document.querySelectorAll('.metric-card').forEach(function (card) {
    card.addEventListener('pointermove', function (e) {
      var r = card.getBoundingClientRect();
      card.style.setProperty('--cx', (e.clientX - r.left) + 'px');
      card.style.setProperty('--cy', (e.clientY - r.top) + 'px');
    });
  });

  /* 6. Image explorer: tabs, slider and auto-motion (self-contained).
     common.js may also have listeners on these elements. To avoid two
     handlers fighting (which caused both dates to show at once), the tabs
     and slider are replaced with clean clones that carry no old listeners. */
  (function initExplorer() {
    var viewer = document.getElementById('radar-viewer');
    var stage = document.getElementById('compare-stage');
    var clip = document.getElementById('radar-after-clip');
    var divider = document.getElementById('compare-divider');
    var single = document.getElementById('single-layer');
    var singleCap = document.getElementById('single-layer-caption');
    var caption = document.getElementById('viewer-caption');
    var oldRange = document.getElementById('compare-range');
    if (!viewer || !stage || !clip || !divider || !single || !singleCap || !oldRange) return;

    /* Set to true if the slider should stay still for visitors who use the
       "reduce motion" system setting. */
    var RESPECT_REDUCED_MOTION = false;

    /* Hide with !important so no other stylesheet can keep an element visible. */
    function setShown(el, shown) {
      el.hidden = !shown;
      if (shown) el.style.removeProperty('display');
      else el.style.setProperty('display', 'none', 'important');
    }

    var range = oldRange.cloneNode(true);
    oldRange.parentNode.replaceChild(range, oldRange);

    var tabs = Array.prototype.map.call(document.querySelectorAll('.layer-tab[data-layer]'), function (t) {
      var c = t.cloneNode(true);
      t.parentNode.replaceChild(c, t);
      return c;
    });

    var LAYERS = {
      before: { src: 'img/pre.png', label: '14 JUL / BEFORE', alt: 'NISAR L-band radar scene from 14 July 2026, before the flash flood', text: 'Showing only the 14 July 2026 scene, before the flood.' },
      after:  { src: 'img/post.png', label: '26 JUL / AFTER', alt: 'NISAR L-band radar scene from 26 July 2026, after the flash flood', text: 'Showing only the 26 July 2026 scene, four days after the flood peak.' },
      change: { src: 'img/change.png', label: 'BACKSCATTER CHANGE', alt: 'NISAR radar backscatter change image, 14 to 26 July 2026', text: 'Showing the backscatter change layer (14 July to 26 July).' }
    };
    var COMPARE_TEXT = 'Drag the divider to compare the 14 July and 26 July scenes.';

    /* slider -> divider position + clip of the "after" image */
    function applyPosition() {
      var v = Math.max(0, Math.min(100, parseFloat(range.value) || 0));
      clip.style.clipPath = 'inset(0 0 0 ' + v + '%)';
      divider.style.left = v + '%';
    }
    range.addEventListener('input', applyPosition);
    applyPosition();

    /* auto-motion */
    var running = false, raf = null;
    function stopAuto() {
      running = false;
      if (raf !== null) { cancelAnimationFrame(raf); raf = null; }
    }
    function startAuto() {
      stopAuto();
      if (RESPECT_REDUCED_MOTION && reduce) return;
      running = true;
      var cur = (parseFloat(range.value) - 50) / 24;
      var phase = Math.asin(Math.max(-1, Math.min(1, cur))); /* continue from current spot */
      var t0 = null;
      function frame(t) {
        if (!running) return;
        if (t0 === null) t0 = t;
        var p = ((t - t0) % 4000) / 4000;
        range.value = (50 + Math.sin(phase + p * Math.PI * 2) * 24).toFixed(1);
        applyPosition();
        raf = requestAnimationFrame(frame);
      }
      raf = requestAnimationFrame(frame);
    }
    /* the visitor takes control: stop moving (only real user input, not our own updates) */
    ['pointerdown', 'touchstart', 'keydown'].forEach(function (ev) {
      range.addEventListener(ev, stopAuto, { passive: true });
    });

    /* layer switching: exactly one view is visible at a time */
    function setLayer(name) {
      tabs.forEach(function (t) {
        var on = t.getAttribute('data-layer') === name;
        t.classList.toggle('is-active', on);
        t.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
      if (name === 'compare') {
        setShown(single, false);
        setShown(singleCap, false);
        setShown(stage, true);
        range.disabled = false;
        caption.textContent = COMPARE_TEXT;
        startAuto();
      } else {
        var L = LAYERS[name];
        if (!L) return;
        stopAuto();
        setShown(stage, false);
        range.disabled = true;
        single.src = L.src;
        single.alt = L.alt;
        setShown(single, true);
        singleCap.textContent = L.label;
        setShown(singleCap, true);
        caption.textContent = L.text;
      }
    }
    tabs.forEach(function (t) {
      t.addEventListener('click', function () { setLayer(t.getAttribute('data-layer')); });
    });

    /* initial state */
    setLayer('compare');
  })();
})();