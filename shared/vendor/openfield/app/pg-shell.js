/* ============================================================================
   DEEPWORK AI · PLANOGRAM — sidebar shell
   Injects the consistent sidebar. Active item from <body data-screen="...">.
   Lucide-style icons, 1.5px stroke (OpenKT iconography rules).
   ============================================================================ */
(function () {
  const I = {
    dashboard: '<path d="M3 3h7v7H3z"/><path d="M14 3h7v7h-7z"/><path d="M14 14h7v7h-7z"/><path d="M3 14h7v7H3z"/>',
    shelves:   '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
    analytics: '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
    products:  '<path d="M2 7h20M7 7V4a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v3M4 7l1.5 13a1 1 0 0 0 1 .9h11a1 1 0 0 0 1-.9L20 7"/><path d="M9 11v5M15 11v5"/>',
    stores:    '<path d="m2 7 4.41-4.41A2 2 0 0 1 7.83 2h8.34a2 2 0 0 1 1.42.59L22 7"/><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M2 7h20"/><path d="M12 7v15"/>',
    settings:  '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
    ask:       '<path d="M9.94 4.66a1 1 0 0 1 1.9 0l1.07 3.2a1 1 0 0 0 .63.64l3.2 1.06a1 1 0 0 1 0 1.9l-3.2 1.07a1 1 0 0 0-.63.63l-1.07 3.2a1 1 0 0 1-1.9 0l-1.06-3.2a1 1 0 0 0-.64-.63l-3.2-1.07a1 1 0 0 1 0-1.9l3.2-1.06a1 1 0 0 0 .64-.64Z"/><path d="M18 5h.01M19 12h.01"/>',
    catalog:   '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
    chev:      '<path d="m6 9 6 6 6-6"/>',
    activity:  '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>',
    logout:    '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
  };
  const svg = (p, w) => `<svg class="ico" width="${w||18}" height="${w||18}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;

  const NAV = [
    ['dashboard', 'Dashboard', 'planogram-dashboard.html'],
    ['ask',       'Ask',       'planogram-ask.html'],
    ['shelves',   'Shelves',   'planogram-shelves.html'],
    ['analytics', 'Analytics', 'planogram-analytics.html'],
    ['products',  'Products',  'planogram-products.html'],
    ['catalog',   'Catalog',   'planogram-catalog.html'],
    ['stores',    'Stores',    'planogram-stores.html'],
    ['settings',  'Settings',  '#'],
  ];

  const active = document.body.dataset.screen || 'dashboard';
  const badge = (document.body.dataset.badge || '').split(',');

  const nav = NAV.map(([key, label, href]) => {
    const on = key === active ? ' on' : '';
    const feat = key === 'ask' ? ' feature' : '';
    const bd = badge.includes(key) ? '<span class="badge"></span>' : '';
    return `<a href="${href}" class="${on}${feat}">${svg(I[key])}<span>${label}</span>${bd}</a>`;
  }).join('');

  const html = `
    <div class="sb-brand">
      <div class="logo">d.</div>
      <div>
        <div class="name">Deepwork AI</div>
        <div class="slug">retail intelligence</div>
      </div>
    </div>

    <div class="sb-user">
      <div class="av">A</div>
      <div>
        <div class="email">admin@villa.com</div>
        <div class="role">Manager</div>
      </div>
    </div>

    <div class="sb-store">
      <div class="lbl"><span class="dot"></span> Active store</div>
      <div class="pick">
        ${svg(I.stores, 16)}
        <span class="txt">Villa Market Sukhumvit 33</span>
        ${svg(I.chev, 15)}
      </div>
    </div>

    <nav class="sb-nav">
      <div class="lbl">Navigation</div>
      ${nav}
    </nav>

    <div class="sb-foot">
      <a href="#">${svg(I.activity, 16)}<span>Developer view</span></a>
      <a href="#">${svg(I.logout, 16)}<span>Sign out</span></a>
    </div>
  `;

  const aside = document.createElement('aside');
  aside.className = 'sidebar';
  aside.innerHTML = html;
  const app = document.querySelector('.app');
  if (app) app.prepend(aside);

  /* ── COMMAND PALETTE (⌘K) ────────────────────────────────── */
  const CMDS = [
    ['Go to', 'Dashboard', '⌘1', 'planogram-dashboard.html', I.dashboard],
    ['Go to', 'Ask — retail intelligence', '⌘2', 'planogram-ask.html', I.ask],
    ['Go to', 'Shelves', '', 'planogram-shelves.html', I.shelves],
    ['Go to', 'Analytics', '', 'planogram-analytics.html', I.analytics],
    ['Go to', 'Products', '', 'planogram-products.html', I.products],
    ['Go to', 'Catalog — all 5,296 SKUs', '', 'planogram-catalog.html', I.catalog],
    ['Go to', 'Stores', '', 'planogram-stores.html', I.stores],
    ['Action', 'Review queue — Dairy (22 items)', '', 'planogram-review.html', I.ask],
    ['Action', 'Upload a shelf photo', '', 'planogram-shelves.html', I.shelves],
    ['Action', 'Open Dairy planogram', '', 'planogram-detail.html', I.shelves],
    ['Shelf', 'Dairy · 446 items', '', 'planogram-detail.html', I.shelves],
    ['Shelf', 'Beer Wine and Spirits · 1492 items', '', 'planogram-detail.html', I.shelves],
    ['Shelf', 'Grocery · 4684 items', '', 'planogram-detail.html', I.shelves],
    ['Product', 'Grated Parmesan · Mainland', '', 'planogram-products.html', I.products],
    ['Product', 'Dom Perignon · Moet & Chandon', '', 'planogram-products.html', I.products],
    ['Product', 'Schiefer Riesling · Nik Weis', '', 'planogram-products.html', I.products],
  ];
  const cmScrim = document.createElement('div');
  cmScrim.className = 'cmdk-scrim';
  cmScrim.innerHTML = `<div class="cmdk" role="dialog">
    <div class="cmdk-input">${svg('<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',18)}
      <input id="cmdkInput" placeholder="Search shelves, products, actions…" autocomplete="off"/>
      <span class="esc">ESC</span></div>
    <div class="cmdk-results" id="cmdkResults"></div>
  </div>`;
  document.body.appendChild(cmScrim);
  const cmInput = cmScrim.querySelector('#cmdkInput');
  const cmResults = cmScrim.querySelector('#cmdkResults');
  let cmSel = 0, cmFiltered = [];

  function cmRender() {
    const q = cmInput.value.trim().toLowerCase();
    cmFiltered = CMDS.filter(c => !q || c[1].toLowerCase().includes(q) || c[0].toLowerCase().includes(q));
    if (cmSel >= cmFiltered.length) cmSel = 0;
    if (!cmFiltered.length) { cmResults.innerHTML = '<div class="cmdk-empty">No matches. Try “review”, “Dairy”, or “upload”.</div>'; return; }
    let out = '', lastG = '';
    cmFiltered.forEach((c, i) => {
      if (c[0] !== lastG) { out += `<div class="cmdk-group">${c[0]}</div>`; lastG = c[0]; }
      out += `<div class="cmdk-item ${i===cmSel?'sel':''}" data-i="${i}">${svg(c[4],18)}<span class="lbl">${c[1]}</span>${c[2]?`<span class="hint">${c[2]}</span>`:''}</div>`;
    });
    cmResults.innerHTML = out;
    cmResults.querySelectorAll('.cmdk-item').forEach(el => {
      el.onmouseenter = () => { cmSel = +el.dataset.i; cmResults.querySelectorAll('.cmdk-item').forEach(x=>x.classList.toggle('sel', x===el)); };
      el.onclick = () => cmGo(+el.dataset.i);
    });
  }
  function cmGo(i) { const c = cmFiltered[i]; if (c) location.href = c[3]; }
  function cmOpen() { cmScrim.classList.add('open'); cmInput.value=''; cmSel=0; cmRender(); setTimeout(()=>cmInput.focus(),30); }
  function cmClose() { cmScrim.classList.remove('open'); }
  window.openCmdK = cmOpen;
  const cmBtn = document.getElementById('cmdkBtn'); if (cmBtn) cmBtn.addEventListener('click', cmOpen);

  cmInput.addEventListener('input', cmRender);
  cmScrim.addEventListener('click', e => { if (e.target === cmScrim) cmClose(); });
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); cmScrim.classList.contains('open') ? cmClose() : cmOpen(); return; }
    if (!cmScrim.classList.contains('open')) return;
    if (e.key === 'Escape') cmClose();
    else if (e.key === 'ArrowDown') { e.preventDefault(); cmSel = Math.min(cmFiltered.length-1, cmSel+1); cmRender(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); cmSel = Math.max(0, cmSel-1); cmRender(); }
    else if (e.key === 'Enter') { e.preventDefault(); cmGo(cmSel); }
  });
  // sidebar store-pick affordance
  const pick = aside.querySelector('.sb-store .pick');
  if (pick) { const k = document.createElement('span'); k.className = 'kbd'; k.textContent = '⌘K'; pick.appendChild(k); pick.style.cursor='pointer'; pick.addEventListener('click', cmOpen); }
})();
