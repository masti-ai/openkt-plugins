/* ============================================================================
   OpenKT demo helpers — tabs + a knowledge-graph canvas with click-to-inspect.
   Zero build step. The only external dependency is vis-network, which the page
   loads from a <script> tag (CDN or vendored). Everything here is plain DOM.

   Usage in a page:
     <script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
     <script src="openkt-demo.js"></script>
     <script>
       OpenKTDemo.tabs();                       // wires [data-tab] buttons → [data-panel]
       OpenKTDemo.graph('graph0', 'detail0', {  // nodes/edges → vis-network + detail panel
         nodes: [{id:'m1', type:'memory', label:'…', body:'raw text', kb:'KB name'},
                 {id:'k1', type:'kb', label:'KB name', body:'summary'},
                 {id:'p1', type:'person', label:'Pratham', body:'12 memories'}],
         edges: [{from:'m1', to:'k1'}, {from:'p1', to:'m1'}]
       });
     </script>
   ============================================================================ */
(function (global) {
  // Palette pulled to match openkt-pages tokens (amber accent, warm ink).
  var STYLE = {
    memory:  { shape: 'dot',      size: 9,  color: '#9a958c', font: { size: 11 } },
    kb:      { shape: 'square',   size: 16, color: '#c0612e', font: { size: 13, color: '#2a2622' } },
    person:  { shape: 'diamond',  size: 14, color: '#2e6fc0', font: { size: 12, color: '#2a2622' } },
    edge:    { color: '#c0612e', opacity: 0.35 }
  };

  function tabs(root) {
    root = root || document;
    var btns = [].slice.call(root.querySelectorAll('[data-tab]'));
    var panels = [].slice.call(root.querySelectorAll('[data-panel]'));
    function show(key) {
      btns.forEach(function (b) { b.classList.toggle('active', b.getAttribute('data-tab') === key); });
      panels.forEach(function (p) { p.hidden = p.getAttribute('data-panel') !== key; });
    }
    btns.forEach(function (b) { b.addEventListener('click', function () { show(b.getAttribute('data-tab')); }); });
    if (btns.length) show(btns[0].getAttribute('data-tab'));
    return { show: show };
  }

  function graph(graphId, detailId, data, opts) {
    opts = opts || {};
    var el = document.getElementById(graphId);
    var detail = detailId ? document.getElementById(detailId) : null;
    if (!el || !global.vis) return null;

    var byId = {};
    var nodes = (data.nodes || []).map(function (n) {
      byId[n.id] = n;
      var s = STYLE[n.type] || STYLE.memory;
      return {
        id: n.id, label: n.short || (n.type === 'memory' ? '' : n.label),
        title: n.label, shape: s.shape, size: s.size,
        color: { background: n.color || s.color, border: n.color || s.color },
        font: s.font
      };
    });
    var edges = (data.edges || []).map(function (e) {
      return { from: e.from, to: e.to, color: { color: STYLE.edge.color, opacity: STYLE.edge.opacity }, width: e.width || 1, dashes: !!e.dashes };
    });

    var network = new global.vis.Network(el, {
      nodes: new global.vis.DataSet(nodes),
      edges: new global.vis.DataSet(edges)
    }, Object.assign({
      physics: { stabilization: true, barnesHut: { gravitationalConstant: -3500, springLength: 110 } },
      interaction: { hover: true, tooltipDelay: 120 },
      nodes: { borderWidth: 0 },
      edges: { smooth: { type: 'continuous' } }
    }, opts.network || {}));

    if (detail) {
      network.on('click', function (params) {
        var id = params.nodes && params.nodes[0];
        if (!id) return;
        var n = byId[id]; if (!n) return;
        detail.innerHTML =
          '<div class="dtype">' + esc(n.type) + '</div>' +
          '<div class="dtitle">' + esc(n.label || '') + '</div>' +
          '<div class="dbody">' + esc(n.body || '') + '</div>' +
          (n.kb ? '<div class="dkb">▦ ' + esc(n.kb) + '</div>' : '');
      });
    }
    return network;
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  global.OpenKTDemo = { tabs: tabs, graph: graph };
})(window);
