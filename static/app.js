(function () {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (!meta) return;
  const CSRF = meta.content;
  const overlay = document.getElementById('overlay');
  const grid = document.getElementById('resultGrid');
  const drawing = document.getElementById('drawing');
  const skipBtn = document.getElementById('skipBtn');
  const closeBtn = document.getElementById('closeBtn');
  const msg = document.getElementById('overlayMsg');
  const box = document.getElementById('box');
  const RARITY = (window.GAME && window.GAME.rarity) || {};
  let audioCtx = null;
  let busy = false;
  let revealTimer = null;

  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, m => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));

  function tone(freq, start, dur, type, gain) {
    const t0 = audioCtx.currentTime + start;
    const osc = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    osc.type = type || 'sine';
    osc.frequency.value = freq;
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.linearRampToValueAtTime(gain || 0.06, t0 + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(g).connect(audioCtx.destination);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  }

  function playFor(maxRarity) {
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      if (maxRarity >= 5) {
        [523, 659, 784, 1047].forEach((f, i) => tone(f, i * 0.085, 0.55, 'triangle', 0.07));
        tone(2093, 0.05, 0.9, 'sine', 0.03);
      } else if (maxRarity >= 3) {
        tone(660, 0, 0.18, 'sine', 0.05);
        tone(880, 0.1, 0.24, 'sine', 0.05);
      } else {
        tone(330, 0, 0.12, 'sine', 0.035);
      }
    } catch (e) { /* 浏览器未授权音频时静默 */ }
  }

  function cardHTML(c, index) {
    const meta = RARITY[String(c.rarity)] || { name: '' };
    const art = c.image
      ? '<img class="card-art" src="' + esc(c.image) + '" alt="">'
      : '<div class="card-emoji">' + esc(c.emoji) + '</div>';
    const badges = [];
    if (c.is_new) badges.push('<span class="badge new">NEW</span>');
    if (c.is_pity) badges.push('<span class="badge pity">保底</span>');
    if (c.count > 1) badges.push('<span class="badge">×' + c.count + '</span>');
    // 稀有度配色交给 CSS 的 .r1~.r5，主题切换时能自动换色
    return '<article class="card r' + c.rarity + '" style="--i:' + index + '">' +
      '<div class="card-top"><span>' + esc(meta.name) + '</span></div>' +
      art +
      '<h3>' + esc(c.name) + '</h3>' +
      '<p class="desc">' + esc(c.description) + '</p>' +
      (badges.length ? '<div class="badges">' + badges.join('') + '</div>' : '') +
      '</article>';
  }

  function updateStats(data) {
    ['coinNum', 'statCoins'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.textContent = data.coins;
    });
    const pity = document.getElementById('statPity');
    if (pity) pity.textContent = data.pity + ' / ' + data.pity_limit;
    const bar = document.getElementById('pityBar');
    if (bar) bar.style.width = (data.pity / data.pity_limit * 100) + '%';
  }

  function resetOverlay() {
    grid.innerHTML = '';
    grid.classList.remove('instant');
    drawing.hidden = false;
    skipBtn.hidden = false;
    closeBtn.hidden = true;
    msg.hidden = true;
    msg.textContent = '';
    if (revealTimer) { clearTimeout(revealTimer); revealTimer = null; }
  }

  function showError(text) {
    drawing.hidden = true;
    skipBtn.hidden = true;
    msg.hidden = false;
    msg.textContent = text;
    closeBtn.hidden = false;
    closeBtn.textContent = '知道了';
  }

  async function draw(mode) {
    if (busy) return;
    busy = true;
    overlay.hidden = false;
    resetOverlay();
    if (box) box.classList.add('shake');
    const body = new FormData();
    body.append('_csrf', CSRF);
    body.append('mode', mode);
    try {
      const res = await fetch('/draw', {
        method: 'POST',
        body: body,
        headers: { 'X-CSRF-Token': CSRF }
      });
      if (res.status === 401) { location.href = '/login'; return; }
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) {
        showError(data.error || '抽卡失败，请稍后重试');
        return;
      }
      drawing.hidden = true;
      grid.innerHTML = data.cards.map(cardHTML).join('');
      updateStats(data);
      playFor(Math.max.apply(null, data.cards.map(c => c.rarity)));
      const delay = data.cards.length * 90 + 620;
      revealTimer = setTimeout(function () {
        closeBtn.hidden = false;
        closeBtn.textContent = '收下';
        skipBtn.hidden = true;
      }, delay);
    } catch (e) {
      showError('网络异常，请重试');
    } finally {
      busy = false;
      if (box) box.classList.remove('shake');
    }
  }

  document.querySelectorAll('[data-mode]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (!overlay.hidden) return;
      draw(btn.getAttribute('data-mode'));
    });
  });

  if (skipBtn) {
    skipBtn.addEventListener('click', function () {
      grid.classList.add('instant');
      skipBtn.hidden = true;
      closeBtn.hidden = false;
      closeBtn.textContent = '收下';
      if (revealTimer) { clearTimeout(revealTimer); revealTimer = null; }
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', function () {
      overlay.hidden = true;
      if (closeBtn.textContent === '收下') {
        location.reload();
      } else {
        resetOverlay();
        overlay.hidden = true;
      }
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !overlay.hidden) {
      overlay.hidden = true;
      resetOverlay();
      location.reload();
    }
  });
})();
