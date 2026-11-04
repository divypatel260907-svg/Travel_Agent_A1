/**
 * Travel Planner AI — main.js
 * Profile modal · localStorage · chip fill · AJAX plan fetch · result render
 */

/* ── Remove curtain from DOM after it finishes fading (2.3 s total) ── */
(function () {
  const curtain = document.getElementById('ch-curtain');
  if (!curtain) return;
  curtain.addEventListener('animationend', () => curtain.remove(), { once: true });
})();

/* ── Auto-dismiss flash messages after 6 s ──────────────────────────────── */
document.querySelectorAll('.flash').forEach(el => {
  setTimeout(() => {
    el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    el.style.opacity = '0';
    el.style.transform = 'translateY(-4px)';
    setTimeout(() => el.remove(), 400);
  }, 6000);
});

/* ── Score bar colour (plan.html) ────────────────────────────────────────── */
document.querySelectorAll('.day-card').forEach(card => {
  const scoreEl = card.querySelector('.day-score');
  if (!scoreEl) return;
  const color = scoreEl.style.color;
  card.querySelectorAll('.score-seg.filled').forEach(seg => {
    seg.style.background = color;
  });
});

/* ── Smooth scroll to #plan ──────────────────────────────────────────────── */
if (window.location.hash === '#plan') {
  document.querySelector('#plan')?.scrollIntoView({ behavior: 'smooth' });
}

/* ════════════════════════════════════════════════════════════════════════════
   PROFILE MODAL
   ════════════════════════════════════════════════════════════════════════════ */
const PROFILE_KEY = 'travel-profile';

function openProfile() {
  const saved = loadProfileData();
  if (saved) populateProfileForm(saved);
  document.getElementById('profile-backdrop').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeProfile(e) {
  if (e && e.target !== document.getElementById('profile-backdrop')) return;
  document.getElementById('profile-backdrop').classList.add('hidden');
  document.body.style.overflow = '';
}

function saveProfile() {
  const data = {
    name:      document.getElementById('p-name').value.trim(),
    city:      document.getElementById('p-city').value.trim(),
    budget:    document.getElementById('p-budget').value,
    style:     document.getElementById('p-style').value,
    group:     document.getElementById('p-group').value,
    diet:      document.getElementById('p-diet').value.trim(),
    interests: document.getElementById('p-interests').value.trim(),
    mobility:  document.getElementById('p-mobility').checked,
  };
  localStorage.setItem(PROFILE_KEY, JSON.stringify(data));
  updateProfileAvatar(data.name);

  // Cross-device sync: save to database if authenticated
  fetch('/auth/profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).catch(() => {});

  document.getElementById('profile-backdrop').classList.add('hidden');
  document.body.style.overflow = '';
}

function loadProfileData() {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function populateProfileForm(d) {
  document.getElementById('p-name').value      = d.name      || '';
  document.getElementById('p-city').value      = d.city      || '';
  document.getElementById('p-budget').value    = d.budget    || '';
  document.getElementById('p-style').value     = d.style     || '';
  document.getElementById('p-group').value     = d.group     || '';
  document.getElementById('p-diet').value      = d.diet      || '';
  document.getElementById('p-interests').value = d.interests || '';
  document.getElementById('p-mobility').checked = !!d.mobility;
}

function updateProfileAvatar(name) {
  const el = document.getElementById('profile-avatar');
  if (!el) return;
  el.textContent = name ? name.charAt(0).toUpperCase() : '👤';
}

/* Prefill & DB sync on page load */
(function () {
  const saved = loadProfileData();
  if (saved) updateProfileAvatar(saved.name);

  // Sync profile from database for logged in user (cross-device support)
  fetch('/auth/profile')
    .then(r => r.ok ? r.json() : null)
    .then(res => {
      if (res && res.preferences && Object.keys(res.preferences).length > 0) {
        localStorage.setItem(PROFILE_KEY, JSON.stringify(res.preferences));
        populateProfileForm(res.preferences);
        if (res.display_name) updateProfileAvatar(res.display_name);
      }
    })
    .catch(() => {});

  // Check if user came from a personalized recommendation chip
  const prefill = sessionStorage.getItem('prefill_prompt');
  if (prefill) {
    const ta = document.getElementById('query');
    if (ta) {
      ta.value = prefill;
      sessionStorage.removeItem('prefill_prompt');
      setTimeout(() => {
        ta.focus();
        ta.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 350);
    }
  }
})();

/* Keyboard close */
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.getElementById('profile-backdrop')?.classList.add('hidden');
    document.body.style.overflow = '';
  }
});

/* ════════════════════════════════════════════════════════════════════════════
   CHIP FILL
   ════════════════════════════════════════════════════════════════════════════ */
document.querySelectorAll('.chip').forEach(btn => {
  btn.addEventListener('click', () => {
    const ta = document.getElementById('query');
    if (!ta) return;
    ta.value = btn.dataset.prompt || '';
    ta.focus();
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('form-section')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  });
});

/* ════════════════════════════════════════════════════════════════════════════
   PLAN FETCH + RENDER
   ════════════════════════════════════════════════════════════════════════════ */

function setLoading(on) {
  const btn     = document.getElementById('submit-btn');
  const btnText = btn?.querySelector('.btn-text');
  const loader  = btn?.querySelector('.btn-loader');
  const result  = document.getElementById('plan-result');

  if (on) {
    if (btn)     { btn.disabled = true; }
    if (btnText) { btnText.textContent = 'Planning…'; }
    if (loader)  { loader.classList.remove('hidden'); }
    if (result)  {
      result.classList.remove('hidden');
      result.innerHTML = `<div class="plan-loading"><div class="plan-spinner"></div></div>`;
      result.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  } else {
    if (btn)     { btn.disabled = false; }
    if (btnText) { btnText.textContent = '✈️\u00a0 Plan my trip'; }
    if (loader)  { loader.classList.add('hidden'); }
  }
}

let currentPlanData = null;
let currentQueryText = '';

async function submitPlan() {
  const ta = document.getElementById('query');
  const query = ta?.value.trim();
  if (!query) { ta?.focus(); return; }
  currentQueryText = query;

  const profile = loadProfileData();
  setLoading(true);

  try {
    const res = await fetch('/api/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, profile: profile || {} }),
    });
    const json = await res.json();
    setLoading(false);

    if (!res.ok || json.error) {
      renderError(json.error || `Server error ${res.status}`);
    } else {
      currentPlanData = json.plan || json;
      renderPlan(currentPlanData);
    }
  } catch (err) {
    setLoading(false);
    renderError('Network error — could not reach the server. Is it running?');
  }
}

function renderError(msg) {
  const result = document.getElementById('plan-result');
  if (!result) return;
  result.classList.remove('hidden');
  result.innerHTML = `
    <div class="plan-error">
      <strong>⚠️ Could not generate plan</strong>
      ${escHtml(msg)}
    </div>`;
  result.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderPlan(plan) {
  const result = document.getElementById('plan-result');
  if (!result) return;

  const days = (plan.days || []).map((d, i) => `
    <div class="plan-day-card" id="day-card-${i}">
      <div class="plan-day-head" onclick="toggleDay(${i})">
        <span class="plan-day-name">${escHtml(d.day || 'Day ' + (i+1))}</span>
        <div style="display:flex;gap:8px;align-items:center">
          ${d.cost ? `<span class="plan-day-cost">${escHtml(d.cost)}</span>` : ''}
          <span class="plan-day-chevron">▼</span>
        </div>
      </div>
      <div class="plan-day-body">
        ${d.morning   ? `<div class="plan-time-slot"><span class="plan-slot-label">Morning</span><span class="plan-slot-text">${escHtml(d.morning)}</span></div>`   : ''}
        ${d.afternoon ? `<div class="plan-time-slot"><span class="plan-slot-label">Afternoon</span><span class="plan-slot-text">${escHtml(d.afternoon)}</span></div>` : ''}
        ${d.evening   ? `<div class="plan-time-slot"><span class="plan-slot-label">Evening</span><span class="plan-slot-text">${escHtml(d.evening)}</span></div>`   : ''}
      </div>
    </div>`).join('');

  const tipsHtml = Array.isArray(plan.tips) && plan.tips.length
    ? `<ul class="plan-tips-list">${plan.tips.map(t => `<li>${escHtml(t)}</li>`).join('')}</ul>`
    : `<p class="plan-footer-card-text">${escHtml(plan.tips || '—')}</p>`;

  result.classList.remove('hidden');
  result.innerHTML = `
    <div class="plan-header">
      <div class="plan-header-label">YOUR AI TRAVEL PLAN</div>
      <p class="plan-summary">${escHtml(plan.summary || '')}</p>
      <div class="plan-meta-row">
        ${plan.budget      ? `<span class="plan-meta-pill">💰 <strong>Budget</strong></span>` : ''}
        ${plan.weatherNote ? `<span class="plan-meta-pill">🌤️ <strong>Weather note</strong></span>` : ''}
        ${(plan.days||[]).length ? `<span class="plan-meta-pill">📅 <strong>${plan.days.length} days</strong></span>` : ''}
      </div>
    </div>

    <div class="plan-days-label">DAY-BY-DAY ITINERARY</div>
    <div class="plan-days">${days}</div>

    <div class="plan-footer-cards">
      <div class="plan-footer-card">
        <div class="plan-footer-card-label">💰 Budget Breakdown</div>
        <p class="plan-footer-card-text">${escHtml(plan.budget || '—')}</p>
      </div>
      <div class="plan-footer-card">
        <div class="plan-footer-card-label">🌤️ Weather Note</div>
        <p class="plan-footer-card-text">${escHtml(plan.weatherNote || '—')}</p>
      </div>
      <div class="plan-footer-card" style="grid-column:1/-1">
        <div class="plan-footer-card-label">💡 Pro Tips</div>
        ${tipsHtml}
      </div>
    </div>

    <!-- Action Row: Save to DB & Share -->
    <div style="margin-top:28px;display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
      <button class="btn btn-primary" id="save-plan-btn" onclick="saveCurrentPlan(this)" style="padding:10px 22px;">
        💾 Save to My Trips
      </button>
      <button class="btn btn-ghost" id="share-plan-btn" onclick="shareCurrentPlan(this)" style="padding:10px 18px;">
        🔗 Share Plan
      </button>
    </div>`;

  // Auto-open Day 1
  const first = document.getElementById('day-card-0');
  if (first) first.classList.add('open');

  result.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function saveCurrentPlan(btn) {
  if (!currentPlanData) return;
  const originalHtml = btn.innerHTML;
  btn.innerHTML = 'Saving…';
  btn.disabled = true;

  try {
    const res = await fetch('/trips/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: currentPlanData.summary || 'My Saved Journey',
        query: currentQueryText || 'AI Planned Trip',
        plan: currentPlanData,
      }),
    });

    if (res.status === 401 || res.redirected) {
      btn.innerHTML = originalHtml;
      btn.disabled = false;
      if (confirm('Please log in or register to save trips to your account.\n\nWould you like to go to the login page now?')) {
        window.location.href = '/auth/login?next=' + encodeURIComponent(window.location.pathname);
      }
      return;
    }

    const json = await res.json();
    if (json.success) {
      btn.innerHTML = '✓ Saved to Account!';
      btn.style.background = 'var(--success)';
      btn.style.color = '#000';
      setTimeout(() => {
        btn.innerHTML = 'View in My Trips →';
        btn.disabled = false;
        btn.onclick = () => { window.location.href = json.url || '/trips/'; };
      }, 1200);
    } else {
      alert(json.error || 'Could not save trip.');
      btn.innerHTML = originalHtml;
      btn.disabled = false;
    }
  } catch (err) {
    btn.innerHTML = originalHtml;
    btn.disabled = false;
    alert('Failed to connect to server.');
  }
}

async function shareCurrentPlan(btn) {
  // If already saved, we can fetch share link; if not, prompt user
  btn.innerHTML = 'Generating link…';
  try {
    // Attempt to save first if not saved
    const res = await fetch('/trips/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: currentPlanData?.summary || 'My Shared Journey',
        query: currentQueryText || 'AI Planned Trip',
        plan: currentPlanData,
      }),
    });

    if (res.status === 401 || res.redirected) {
      btn.innerHTML = '🔗 Share Plan';
      if (confirm('Please log in or register to generate shareable links for your trips.\n\nGo to Login now?')) {
        window.location.href = '/auth/login?next=' + encodeURIComponent(window.location.pathname);
      }
      return;
    }

    const json = await res.json();
    if (json.success && json.trip_id) {
      const shareRes = await fetch(`/trips/${json.trip_id}/share`, { method: 'POST' });
      const shareJson = await shareRes.json();
      if (shareJson.url) {
        navigator.clipboard.writeText(shareJson.url).catch(() => {});
        btn.innerHTML = '✓ Link Copied!';
        setTimeout(() => { btn.innerHTML = '🔗 Share Plan'; }, 2200);
        return;
      }
    }
    btn.innerHTML = '🔗 Share Plan';
  } catch (e) {
    btn.innerHTML = '🔗 Share Plan';
  }
}

function toggleDay(i) {
  const card = document.getElementById('day-card-' + i);
  if (card) card.classList.toggle('open');
}

function loadSamplePlan() {
  if (typeof SAMPLE_PLAN !== 'undefined') {
    currentPlanData = SAMPLE_PLAN;
    currentQueryText = SAMPLE_PLAN.summary;
    renderPlan(SAMPLE_PLAN);
  }
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* ════════════════════════════════════════════════════════════════════════════
   CINEMATIC HERO — scroll-driven fade + plan-nav reveal
   ════════════════════════════════════════════════════════════════════════════ */
(function () {
  const logo     = document.getElementById('ch-logo');
  const title    = document.getElementById('ch-title');
  const planNav  = document.getElementById('plan-nav');
  const scrollCue = document.getElementById('ch-scroll-cue');

  // Only wire up on pages that have the cinematic hero
  if (!logo || !title || !planNav) return;

  // Threshold: hero is 100vh; start fading at 8% scroll, complete at 35%
  const FADE_START  = 0.08;  // fraction of hero height
  const FADE_END    = 0.35;
  const NAV_TRIGGER = 0.18;  // show plan-nav at this point

  let ticking = false;

  function onScroll() {
    if (!ticking) {
      requestAnimationFrame(update);
      ticking = true;
    }
  }

  function update() {
    ticking = false;
    const scrollY   = window.scrollY;
    const heroH     = window.innerHeight;
    const progress  = scrollY / heroH;          // 0 → 1 over one viewport

    // ── Logo: fade out + drift UP ──────────────────────────────────────────
    const logoP  = clamp01((progress - FADE_START) / (FADE_END - FADE_START));
    logo.style.opacity   = String(1 - logoP);
    logo.style.transform = `translateY(${-logoP * 30}px)`;

    // ── Title: fade out + drift DOWN ───────────────────────────────────────
    const titleP = clamp01((progress - FADE_START) / (FADE_END - FADE_START));
    title.style.opacity   = String(1 - titleP);
    title.style.transform = `translateY(${titleP * 30}px)`;

    // ── Scroll cue: fade out early ─────────────────────────────────────────
    if (scrollCue) {
      scrollCue.style.opacity = String(Math.max(0, 1 - progress / 0.12));
    }

    // ── Plan-My-Trip nav: slide in from top ────────────────────────────────
    if (progress >= NAV_TRIGGER) {
      planNav.classList.add('visible');
      planNav.removeAttribute('aria-hidden');
      document.body.classList.add('plan-nav-active');
      // sync profile avatar
      syncPlanNavAvatar();
    } else {
      planNav.classList.remove('visible');
      planNav.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('plan-nav-active');
    }
  }

  function clamp01(v) { return Math.min(1, Math.max(0, v)); }

  // Keep plan-nav profile avatar in sync with the main one
  function syncPlanNavAvatar() {
    const src  = document.getElementById('profile-avatar');
    const dest = document.getElementById('plan-nav-avatar');
    if (src && dest && dest.textContent !== src.textContent) {
      dest.textContent = src.textContent;
    }
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  // Run once on load in case page is loaded mid-scroll
  update();
})();
