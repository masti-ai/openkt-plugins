/* ============================================================================
   OPEN FIELD · loading + agents
   Self-mounting monospace loading vocabulary (Deepwork), adapted.
   - [data-spin="name"]      cycling spinner glyphs
   - [data-bar]              animated progress bar
   - [data-type]             streaming text typer w/ caret
   - .agent-face             blinking + talking ASCII faces (auto from data-face)
   ============================================================================ */
(function () {
  /* ── SPINNERS ─────────────────────────────────────────────── */
  const SPIN = {
    pipe:    { f: ['|','/','-','\\'], ms: 100 },
    braille: { f: ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏'], ms: 80 },
    blocks:  { f: ['▰▱▱▱','▱▰▱▱','▱▱▰▱','▱▱▱▰','▱▱▰▱','▱▰▱▱'], ms: 140 },
    pulse:   { f: ['·','∘','○','◯','○','∘'], ms: 220 },
    moon:    { f: ['◐','◓','◑','◒'], ms: 220 },
    triangle:{ f: ['◢','◣','◤','◥'], ms: 120 },
    square:  { f: ['◰','◳','◲','◱'], ms: 150 },
    level:   { f: ['▁','▂','▃','▄','▅','▆','▇','█','▇','▆','▅','▄','▃','▂'], ms: 90 },
    wave:    { f: ['▁▂▃▄▅▆▇','▂▃▄▅▆▇█','▃▄▅▆▇█▇','▄▅▆▇█▇▆','▅▆▇█▇▆▅','▆▇█▇▆▅▄','▇█▇▆▅▄▃','█▇▆▅▄▃▂'], ms: 80 },
    domino:  { f: ['●○○○○','○●○○○','○○●○○','○○○●○','○○○○●','○○○●○','○○●○○','○●○○○'], ms: 100 },
    bracket: { f: ['[▮     ]','[ ▮    ]','[  ▮   ]','[   ▮  ]','[    ▮ ]','[     ▮]','[    ▮ ]','[   ▮  ]','[  ▮   ]','[ ▮    ]'], ms: 100 },
    ball:    { f: ['(o     )','( o    )','(  o   )','(   o  )','(    o )','(     o)','(    o )','(   o  )','(  o   )','( o    )'], ms: 90 },
    arrow:   { f: ['▸───────','─▸──────','──▸─────','───▸────','────▸───','─────▸──','──────▸─','───────▸'], ms: 90 },
  };
  document.querySelectorAll('[data-spin]').forEach(el => {
    const s = SPIN[el.dataset.spin]; if (!s) return;
    let i = 0;
    el.textContent = s.f[0];
    setInterval(() => { el.textContent = s.f[i % s.f.length]; i++; }, s.ms);
  });

  /* live timer */
  document.querySelectorAll('[data-timer]').forEach(el => {
    const t0 = performance.now();
    setInterval(() => { el.textContent = ((performance.now() - t0) / 1000).toFixed(1) + 's'; }, 100);
  });

  /* ── PROGRESS BARS ────────────────────────────────────────── */
  document.querySelectorAll('[data-bar]').forEach(el => {
    const width = parseInt(el.dataset.width || '24', 10);
    const style = el.dataset.bar || 'block';      // block | half | arrow | file
    const fillEl = el.querySelector('.bar-fill') || el;
    const pctEl  = el.querySelector('.bar-pct');
    const byteEl = el.querySelector('.bar-bytes');
    const total  = 4200000;
    let p = 0;
    const render = () => {
      const filled = Math.round(p * width);
      let s = '';
      if (style === 'block') {
        s = '█'.repeat(filled) + '░'.repeat(width - filled);
      } else if (style === 'half') {
        const exact = p * width;
        const full = Math.floor(exact);
        const half = (exact - full) > 0.5 ? '▌' : '';
        s = '█'.repeat(full) + half + '░'.repeat(Math.max(0, width - full - half.length));
      } else if (style === 'arrow') {
        s = '─'.repeat(Math.max(0, filled - 1)) + (filled > 0 ? '▸' : '') + ' '.repeat(width - filled);
        s = '[' + s + ']';
      } else if (style === 'file') {
        s = '▓'.repeat(filled) + '·'.repeat(width - filled);
      }
      fillEl.textContent = s;
      if (pctEl)  pctEl.textContent = Math.round(p * 100) + '%';
      if (byteEl) byteEl.textContent = Math.round(p * total).toLocaleString() + ' / ' + total.toLocaleString() + ' B';
    };
    render();
    setInterval(() => {
      p += 0.008 + Math.random() * 0.02;
      if (p >= 1) { p = 0; }
      render();
    }, 90);
  });

  /* ── STREAMING TYPER ──────────────────────────────────────── */
  document.querySelectorAll('[data-type]').forEach(el => {
    const full = el.dataset.type;
    const speed = parseInt(el.dataset.typeSpeed || '38', 10);
    const out = document.createElement('span');
    const caret = document.createElement('span');
    caret.className = 'of-caret';
    el.textContent = '';
    el.append(out, caret);
    let i = 0;
    const tick = () => {
      if (i <= full.length) {
        out.textContent = full.slice(0, i);
        i++;
        setTimeout(tick, speed + (full[i - 1] === ' ' ? 30 : 0));
      } else {
        setTimeout(() => { i = 0; out.textContent = ''; tick(); }, 2600);
      }
    };
    tick();
  });

  /* ── AGENT FACES ──────────────────────────────────────────── */
  // Eyes <span class="eye">, mouth <span class="mouth">; we drive them.
  const MOUTHS = {
    a: ['╰○╯','╰◯╯','╰○╯','╰▽╯','╰○╯','╰═╯'],
    b: ['─','·','─','○','─','╌'],
    c: ['⌣','◡','⌣','○','⌣','◡'],
    d: ['‿','○','‿','◡','‿','╌'],
  };
  document.querySelectorAll('.agent-face').forEach((face, n) => {
    const eyes  = face.querySelectorAll('.eye');
    const mouth = face.querySelector('.mouth');
    const mset  = MOUTHS[face.dataset.mouth || 'a'];
    const eyeOpen   = face.dataset.eyeOpen   || '●';
    const eyeClosed = face.dataset.eyeClosed || '─';
    eyes.forEach(e => e.textContent = eyeOpen);
    if (mouth) mouth.textContent = mset[0];
    // talk
    if (mouth) {
      let mi = 0;
      const talk = () => {
        mi = (mi + 1) % mset.length;
        mouth.textContent = mset[mi];
        setTimeout(talk, 90 + Math.random() * 220);
      };
      setTimeout(talk, Math.random() * 500);
    }
    // blink
    const blink = () => {
      eyes.forEach(e => e.textContent = eyeClosed);
      setTimeout(() => eyes.forEach(e => e.textContent = eyeOpen), 130);
      setTimeout(blink, 3500 + Math.random() * 4000);
    };
    setTimeout(blink, 1200 + Math.random() * 3000);
  });
})();
