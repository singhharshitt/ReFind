/**
 * ReFind shared frontend behaviour.
 * Uses event delegation so HTMX-swapped content keeps working.
 */
(function () {
  'use strict';

  function refreshIcons(root) {
    if (window.lucide) {
      window.lucide.createIcons({ nodes: root ? [root] : undefined });
    }
  }

  function dismissToasts() {
    document.querySelectorAll('.toast').forEach(function (toast) {
      setTimeout(function () {
        toast.classList.add('is-leaving');
        setTimeout(function () {
          toast.remove();
        }, 350);
      }, 4000);
    });
  }

  function closeProfileDropdown() {
    var dropdown = document.getElementById('profile-dropdown');
    var btn = document.getElementById('profile-btn');
    if (dropdown) dropdown.classList.remove('is-open');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }

  function closeMobileNav() {
    var drawer = document.getElementById('mobile-nav');
    var toggle = document.getElementById('mobile-nav-toggle');
    var backdrop = document.getElementById('mobile-nav-backdrop');
    if (drawer) drawer.classList.remove('is-open');
    if (backdrop) {
      backdrop.classList.remove('is-open');
      backdrop.hidden = true;
    }
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('nav-open');
  }

  function openMobileNav() {
    var drawer = document.getElementById('mobile-nav');
    var toggle = document.getElementById('mobile-nav-toggle');
    var backdrop = document.getElementById('mobile-nav-backdrop');
    if (drawer) drawer.classList.add('is-open');
    if (backdrop) {
      backdrop.hidden = false;
      backdrop.classList.add('is-open');
    }
    if (toggle) toggle.setAttribute('aria-expanded', 'true');
    document.body.classList.add('nav-open');
  }

  function closeMobileFilters() {
    var panel = document.getElementById('mobile-filters');
    var backdrop = document.getElementById('mobile-filters-backdrop');
    if (panel) panel.classList.remove('is-open');
    if (backdrop) {
      backdrop.classList.remove('is-open');
      backdrop.hidden = true;
    }
    document.body.classList.remove('filters-open');
  }

  function openMobileFilters() {
    var panel = document.getElementById('mobile-filters');
    var backdrop = document.getElementById('mobile-filters-backdrop');
    if (panel) panel.classList.add('is-open');
    if (backdrop) {
      backdrop.hidden = false;
      backdrop.classList.add('is-open');
    }
    document.body.classList.add('filters-open');
  }

  function syncListingTypeFields() {
    var priceField = document.getElementById('price-field');
    var wantedField = document.getElementById('wanted-field');
    if (!priceField || !wantedField) return;
    var selected = document.querySelector('input[name="listing_type"]:checked');
    var val = selected ? selected.value : 'sell';
    priceField.style.display = val === 'sell' ? '' : 'none';
    wantedField.style.display = val === 'exchange' ? '' : 'none';
  }

  document.addEventListener('DOMContentLoaded', function () {
    refreshIcons();
    dismissToasts();
    syncListingTypeFields();

    var msgs = document.getElementById('thread-messages');
    if (msgs) msgs.scrollTop = msgs.scrollHeight;

    var authPage = document.querySelector('.auth-page');
    if (authPage && authPage.dataset.screen) {
      var screen = authPage.dataset.screen;
      document.querySelectorAll('.auth-screen').forEach(function (panel) {
        panel.classList.toggle('is-active', panel.dataset.panel === screen);
      });
    }
  });

  document.body.addEventListener('htmx:afterSwap', function (event) {
    refreshIcons(event.target);
  });

  document.body.addEventListener('htmx:afterSettle', function (event) {
    refreshIcons(event.target);
  });

  function getTheme() {
    return document.documentElement.getAttribute('data-theme') || 'light';
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem('refind-theme', theme);
    } catch (e) { /* ignore */ }
    refreshIcons();
  }

  function toggleTheme() {
    setTheme(getTheme() === 'dark' ? 'light' : 'dark');
  }

  document.addEventListener('click', function (event) {
    if (event.target.closest('#theme-toggle')) {
      toggleTheme();
      return;
    }

    var profileBtn = event.target.closest('#profile-btn');
    if (profileBtn) {
      event.stopPropagation();
      var dropdown = document.getElementById('profile-dropdown');
      if (!dropdown) return;
      var open = dropdown.classList.toggle('is-open');
      profileBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      return;
    }

    if (!event.target.closest('.profile-dropdown-wrapper')) {
      closeProfileDropdown();
    }

    if (event.target.closest('#mobile-nav-toggle')) {
      var drawer = document.getElementById('mobile-nav');
      if (drawer && drawer.classList.contains('is-open')) {
        closeMobileNav();
      } else {
        openMobileNav();
      }
      return;
    }

    if (event.target.closest('[data-close-mobile-nav], #mobile-nav-backdrop')) {
      closeMobileNav();
      return;
    }

    if (event.target.closest('#mobile-filters-toggle')) {
      openMobileFilters();
      return;
    }

    if (event.target.closest('[data-close-mobile-filters], #mobile-filters-backdrop')) {
      closeMobileFilters();
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      closeProfileDropdown();
      closeMobileNav();
      closeMobileFilters();
    }
  });

  // Listing form helpers (price / exchange fields + image preview)
  document.addEventListener('change', function (event) {
    if (event.target.matches('input[name="listing_type"]')) {
      var priceField = document.getElementById('price-field');
      var wantedField = document.getElementById('wanted-field');
      if (!priceField || !wantedField) return;
      var val = event.target.value;
      priceField.style.display = val === 'sell' ? '' : 'none';
      wantedField.style.display = val === 'exchange' ? '' : 'none';
    }

    if (event.target.matches('.image-upload-slot input[type="file"]')) {
      var file = event.target.files && event.target.files[0];
      if (!file) return;
      var label = event.target.closest('.image-upload-slot').querySelector('.image-upload-label');
      if (!label) return;
      var reader = new FileReader();
      reader.onload = function (e) {
        label.innerHTML = '<img class="img-preview" src="' + e.target.result + '" alt="Preview">';
      };
      reader.readAsDataURL(file);
    }
  });

  // Auth screen toggles + password visibility
  document.addEventListener('click', function (event) {
    var go = event.target.closest('[data-go]');
    if (go) {
      var authPage = document.querySelector('.auth-page');
      if (!authPage) return;
      var screen = go.dataset.go;
      authPage.dataset.screen = screen;
      document.querySelectorAll('.auth-screen').forEach(function (panel) {
        panel.classList.toggle('is-active', panel.dataset.panel === screen);
      });
      window.history.replaceState({}, '', window.location.pathname + '?screen=' + screen);
      refreshIcons();
      return;
    }

    var toggle = event.target.closest('.password-toggle');
    if (toggle) {
      var input = toggle.closest('.auth-input').querySelector('input');
      if (input) input.type = input.type === 'password' ? 'text' : 'password';
    }
  });

  window.switchImage = function (btn, url) {
    var main = document.getElementById('main-img');
    if (main) main.src = url;
    document.querySelectorAll('.thumb-btn').forEach(function (b) {
      b.classList.remove('active');
    });
    btn.classList.add('active');
  };
})();
