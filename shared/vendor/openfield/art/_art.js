/* ─────────────────────────────────────────────────────────────
   LAYER 3 · ART LIBRARY
   Each art piece is a function: render(el) -> starts an
   animation loop, writes ascii into el.textContent.
   Drop any of these into any host with class "art-canvas".
   ───────────────────────────────────────────────────────────── */

window.DWArt = (function () {
  function size(el) {
    return {
      W: Math.max(1, Math.floor(el.clientWidth / 7)),
      H: Math.max(1, Math.floor(el.clientHeight / 11))
    };
  }
  const palette = [' ', '·', '·', '∘', '○', '◯', '○', '∘', '·', ' '];

  /* ── BREATH ── slow concentric rings inhale/exhale (calm) */
  function breath(el) {
    function tick() {
      const { W, H } = size(el);
      const t = performance.now() * 0.0005;
      const scale = 1 + Math.sin(t * 1.5) * 0.35;
      const cx = W / 2, cy = H / 2;
      const lines = [];
      for (let y = 0; y < H; y++) {
        let line = '';
        for (let x = 0; x < W; x++) {
          const dx = (x - cx) * 0.5, dy = y - cy;
          const d = Math.sqrt(dx * dx + dy * dy) / scale;
          const idx = Math.floor(d) % palette.length;
          line += palette[idx] + ' ';
        }
        lines.push(line);
      }
      el.textContent = lines.join('\n');
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ── Tunnel ── rings zoom inward (motion forward) */
  function tunnel(el) {
    function tick() {
      const { W, H } = size(el);
      const t = performance.now() * 0.0018;
      const cx = W / 2, cy = H / 2;
      const lines = [];
      for (let y = 0; y < H; y++) {
        let line = '';
        for (let x = 0; x < W; x++) {
          const dx = (x - cx) * 0.5, dy = y - cy;
          const d = Math.sqrt(dx * dx + dy * dy);
          const raw = d - t * 4 + 100;
          const idx = ((Math.floor(raw) % palette.length) + palette.length) % palette.length;
          line += palette[idx] + ' ';
        }
        lines.push(line);
      }
      el.textContent = lines.join('\n');
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ── FLOW ── drifting noise field (organic) */
  function flow(el) {
    const glyphs = [' ', '·', '·', '∘', '○', '◯'];
    function noise(x, y, t) {
      return (
        Math.sin(x * 0.12 + t * 0.0005) +
        Math.cos(y * 0.18 - t * 0.0007) +
        Math.sin((x + y) * 0.09 + t * 0.0004) +
        Math.cos((x - y) * 0.11 - t * 0.0006)
      ) / 4;
    }
    function tick() {
      const { W, H } = size(el);
      const t = performance.now();
      const lines = [];
      for (let y = 0; y < H; y++) {
        let line = '';
        for (let x = 0; x < W; x++) {
          const n = noise(x, y, t);
          const idx = Math.floor((n + 1) / 2 * (glyphs.length - 1));
          line += glyphs[Math.max(0, Math.min(glyphs.length - 1, idx))] + ' ';
        }
        lines.push(line);
      }
      el.textContent = lines.join('\n');
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ── RAIN ── sparse drops falling (data streaming) */
  function rain(el) {
    const drops = [];
    let seeded = false;
    function tick() {
      const { W, H } = size(el);
      if (!seeded) {
        for (let i = 0; i < 18; i++) drops.push({
          col: Math.floor(Math.random() * W),
          row: Math.random() * H,
          speed: 0.04 + Math.random() * 0.1
        });
        seeded = true;
      }
      const g = Array.from({ length: H }, () => Array(W).fill(' '));
      drops.forEach(d => {
        d.row += d.speed;
        if (d.row > H + 2) { d.row = -2; d.col = Math.floor(Math.random() * W); }
        if (d.col < 0 || d.col >= W) d.col = Math.floor(Math.random() * W);
        const r = Math.floor(d.row);
        if (r >= 0 && r < H) g[r][d.col] = '·';
        const r2 = Math.floor(d.row - 1);
        if (r2 >= 0 && r2 < H && g[r2][d.col] === ' ') g[r2][d.col] = '·';
      });
      el.textContent = g.map(r => r.join('')).join('\n');
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ── SPIRAL ── rotating polar curve (focus / attention) */
  function spiral(el) {
    let theta = 0;
    function tick() {
      const { W, H } = size(el);
      const cx = W / 2, cy = H / 2;
      const g = Array.from({ length: H }, () => Array(W).fill(' '));
      for (let t = 0; t < 120; t += 0.1) {
        const r = t * 0.2;
        const x = Math.round(cx + Math.cos(t + theta) * r);
        const y = Math.round(cy + Math.sin(t + theta) * r * 0.55);
        if (x >= 0 && x < W && y >= 0 && y < H) g[y][x] = '·';
      }
      el.textContent = g.map(r => r.join('')).join('\n');
      theta += 0.04;
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ── WAVE ── crossed sines (interference, gentle) */
  function wave(el) {
    function tick() {
      const { W, H } = size(el);
      const t = performance.now() * 0.001;
      const lines = [];
      for (let y = 0; y < H; y++) {
        let line = '';
        for (let x = 0; x < W; x++) {
          const v = Math.sin(x * 0.18 + t) + Math.cos(y * 0.5 - t * 0.7);
          line += (Math.abs(v) < 0.3 ? '·' : ' ') + ' ';
        }
        lines.push(line);
      }
      el.textContent = lines.join('\n');
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ── ORBITS ── three bodies on different periods (relationships) */
  function orbits(el) {
    const wake = [];
    const bodies = [
      { r: 6,  sp: 0.0014, phase: 0,             ch: '◯' },
      { r: 10, sp: 0.0009, phase: Math.PI * 0.7, ch: '○' },
      { r: 14, sp: 0.0006, phase: Math.PI * 1.4, ch: '·' }
    ];
    function tick() {
      const { W, H } = size(el);
      const t = performance.now();
      bodies.forEach(b => {
        const x = Math.round(W / 2 + Math.cos(t * b.sp + b.phase) * b.r);
        const y = Math.round(H / 2 + Math.sin(t * b.sp + b.phase) * b.r * 0.5);
        wake.push({ x, y, born: t });
      });
      while (wake.length && t - wake[0].born > 1600) wake.shift();
      const g = Array.from({ length: H }, () => Array(W).fill(' '));
      g[Math.floor(H / 2)][Math.floor(W / 2)] = '·';
      const order = { ' ': 0, '·': 1, '∘': 2, '○': 3, '◯': 4 };
      wake.forEach(p => {
        if (p.x < 0 || p.x >= W || p.y < 0 || p.y >= H) return;
        const age = (t - p.born) / 1600;
        const ch = age < 0.25 ? '◯' : age < 0.5 ? '○' : age < 0.8 ? '∘' : '·';
        if ((order[ch] || 0) >= (order[g[p.y][p.x]] || 0)) g[p.y][p.x] = ch;
      });
      el.textContent = g.map(r => r.join('')).join('\n');
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ── TYPESWARM ── characters drifting in a noise field (signature) */
  function typeswarm(el, options = {}) {
    const chars = options.chars || 'deepwork labs · one brain · every harness · '.split('');
    function noise(x, y, t) {
      return (
        Math.sin(x * 0.12 + t * 0.0005) +
        Math.cos(y * 0.2 - t * 0.0007) +
        Math.sin((x + y) * 0.09 + t * 0.0004)
      ) / 3;
    }
    function tick() {
      const { W, H } = size(el);
      const t = performance.now();
      const lines = [];
      let i = 0;
      for (let y = 0; y < H; y++) {
        let line = '';
        for (let x = 0; x < W; x++) {
          const n = noise(x, y, t);
          // dense in center band, sparse at edges
          if (Math.abs(n) > 0.55) {
            line += chars[(i + Math.floor(t * 0.005)) % chars.length] + ' ';
          } else if (Math.abs(n) > 0.25) {
            line += '·' + ' ';
          } else {
            line += '  ';
          }
          i++;
        }
        lines.push(line);
      }
      el.textContent = lines.join('\n');
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ── TYPESPIRAL ── letters arranged along a spiral, rotating */
  function typespiral(el, options = {}) {
    const chars = (options.chars || 'deepwork labs one brain every harness  ').split('');
    let theta = 0;
    function tick() {
      const { W, H } = size(el);
      const cx = W / 2, cy = H / 2;
      const g = Array.from({ length: H }, () => Array(W).fill(' '));
      let i = 0;
      for (let t = 0; t < 220; t += 0.32) {
        const r = t * 0.16;
        const x = Math.round(cx + Math.cos(t + theta) * r);
        const y = Math.round(cy + Math.sin(t + theta) * r * 0.55);
        if (x >= 0 && x < W && y >= 0 && y < H) {
          g[y][x] = chars[i % chars.length];
        }
        i++;
      }
      el.textContent = g.map(r => r.join('')).join('\n');
      theta += 0.012;
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ── TYPEFIELD ── full grid of characters whose density follows a wave */
  function typefield(el, options = {}) {
    const chars = (options.chars || 'abcdefghijklmnopqrstuvwxyz').split('');
    function tick() {
      const { W, H } = size(el);
      const t = performance.now() * 0.0008;
      const cx = W / 2, cy = H / 2;
      const lines = [];
      let i = 0;
      for (let y = 0; y < H; y++) {
        let line = '';
        for (let x = 0; x < W; x++) {
          const dx = x - cx, dy = (y - cy) * 1.8;
          const d = Math.sqrt(dx*dx + dy*dy);
          const v = Math.sin(d * 0.4 - t * 2);
          if (v > 0.55) line += chars[(i + Math.floor(t * 8)) % chars.length] + ' ';
          else if (v > 0)  line += '·' + ' ';
          else             line += '  ';
          i++;
        }
        lines.push(line);
      }
      el.textContent = lines.join('\n');
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ── GLYPHRAIN ── characters falling (matrix-style but quiet) */
  function glyphrain(el, options = {}) {
    const chars = (options.chars || 'oOo.·∘○').split('');
    const drops = [];
    let seeded = false;
    function tick() {
      const { W, H } = size(el);
      if (!seeded) {
        for (let i = 0; i < 16; i++) drops.push({
          col: Math.floor(Math.random() * W),
          row: Math.random() * H,
          speed: 0.05 + Math.random() * 0.12,
          ch: chars[Math.floor(Math.random() * chars.length)]
        });
        seeded = true;
      }
      const g = Array.from({ length: H }, () => Array(W).fill(' '));
      drops.forEach(d => {
        d.row += d.speed;
        if (d.row > H + 2) {
          d.row = -2;
          d.col = Math.floor(Math.random() * W);
          d.ch = chars[Math.floor(Math.random() * chars.length)];
        }
        const r = Math.floor(d.row);
        if (r >= 0 && r < H) g[r][d.col] = d.ch;
        const r2 = Math.floor(d.row - 1);
        if (r2 >= 0 && r2 < H && g[r2][d.col] === ' ') g[r2][d.col] = '·';
      });
      el.textContent = g.map(r => r.join('')).join('\n');
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ── TREE ── L-system growth, regenerates every ~5s (organic life) */
  function tree(el) {
    let pts = [], i = 0, timer;
    function buildStr(d) {
      let s = 'F';
      const rules = { 'F': 'FF+[+F-F-F]-[-F+F+F]' };
      for (let k = 0; k < d; k++) s = s.split('').map(c => rules[c] || c).join('');
      return s;
    }
    function rebuild(W, H) {
      const s = buildStr(4);
      const out = [];
      let stack = [], x = W / 2, y = H - 1, angle = -Math.PI / 2;
      const len = 0.42;
      for (const c of s) {
        if (c === 'F') {
          const nx = x + Math.cos(angle) * len;
          const ny = y + Math.sin(angle) * len;
          const steps = Math.max(2, Math.ceil(Math.hypot(nx - x, ny - y) * 2));
          for (let s2 = 1; s2 <= steps; s2++) {
            out.push([
              Math.round(x + (nx - x) * (s2 / steps)),
              Math.round(y + (ny - y) * (s2 / steps))
            ]);
          }
          x = nx; y = ny;
        } else if (c === '+') angle -= 0.42;
        else if (c === '-') angle += 0.42;
        else if (c === '[') stack.push([x, y, angle]);
        else if (c === ']') [x, y, angle] = stack.pop();
      }
      return out;
    }
    function draw() {
      const { W, H } = size(el);
      const g = Array.from({ length: H }, () => Array(W).fill(' '));
      const cap = Math.min(i, pts.length);
      for (let k = 0; k < cap; k++) {
        const [px, py] = pts[k];
        if (px >= 0 && px < W && py >= 0 && py < H) g[py][px] = '·';
      }
      el.textContent = g.map(r => r.join('')).join('\n');
    }
    function start() {
      clearInterval(timer);
      const { W, H } = size(el);
      pts = rebuild(W, H);
      i = 0;
      timer = setInterval(() => {
        i += 32;
        draw();
        if (i >= pts.length) { clearInterval(timer); setTimeout(start, 4000); }
      }, 40);
    }
    start();
  }

  /* ── PHYLLO ── sunflower phyllotaxis (compounded discoveries) */
  function phyllo(el) {
    let rot = 0;
    function tick() {
      const { W, H } = size(el);
      const cx = W / 2, cy = H / 2;
      const phi = Math.PI * (3 - Math.sqrt(5));
      const g = Array.from({ length: H }, () => Array(W).fill(' '));
      for (let k = 0; k < 220; k++) {
        const a = k * phi + rot;
        const r = Math.sqrt(k) * 0.65;
        const x = Math.round(cx + Math.cos(a) * r);
        const y = Math.round(cy + Math.sin(a) * r * 0.55);
        if (x >= 0 && x < W && y >= 0 && y < H) {
          g[y][x] = k < 30 ? '·' : k < 90 ? '∘' : k < 180 ? '○' : '◯';
        }
      }
      el.textContent = g.map(r => r.join('')).join('\n');
      rot += 0.005;
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ── MAP — render any art by name into any element ── */
  const ART = {
    breath, tunnel, flow, rain, spiral, wave, orbits,
    typeswarm, typespiral, typefield, glyphrain, tree, phyllo
  };

  function init(root = document) {
    root.querySelectorAll('[data-art]').forEach(el => {
      const name = el.dataset.art;
      const color = el.dataset.color;
      if (color) el.style.color = color;
      if (ART[name]) ART[name](el);
    });
  }

  return Object.assign(ART, { init, size });
})();

// Auto-init on load
if (document.readyState !== 'loading') window.DWArt.init();
else document.addEventListener('DOMContentLoaded', () => window.DWArt.init());
