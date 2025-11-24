// JavaScript file created by Personal AI Assistant
// Date: 2025-10-16 12:14:05

// Brain visualization and UI state for Bittu
(function(){
  const canvas = document.getElementById('brainCanvas');
  const ctx = canvas ? canvas.getContext('2d') : null;
  const logEl = document.getElementById('log');
  const clearLogBtn = document.getElementById('clearLogBtn');
  const popoutBtn = document.getElementById('popoutBtn');
  const cmdInput = document.getElementById('cmdInput');
  const sendBtn = document.getElementById('sendBtn');
  const dotListening = document.getElementById('dot-listening');
  const dotProcessing = document.getElementById('dot-processing');
  const dotSpeaking = document.getElementById('dot-speaking');
  const statusBar = document.getElementById('statusBar');

  const state = {
    mode: 'idle', // 'idle' | 'listening' | 'processing' | 'speaking'
    t: 0,
    nodes: [],        // neuron points
    axons: [],        // bézier curves between clusters [{p0,p1,c0,c1}]
    packets: [],      // signals traveling along axons
    clusters: [],     // cluster centers
    orbs: [],         // floating decorative orbs
    offset: { x: 0, y: 0 }, // translation to center network
    scale: 1          // uniform scale to fit viewport
  };
  // Professional palette per cluster (teal, aqua, blue, violet, amber, coral)
  const clusterHues = [160, 175, 205, 260, 30, 12];

  function classify(msg){
    const m = String(msg || '');
    if (/^error[:\s]/i.test(m) || /\b❌\b/.test(m)) return 'error';
    if (/^warn[:\s]/i.test(m) || /\b⚠️\b/.test(m)) return 'warn';
    if (/^state[:\s]/i.test(m) || /^(Status:|State:)/i.test(m)) return 'state';
    return '';
  }

  function log(msg){
    if (!logEl) return;
    const time = new Date().toLocaleTimeString();
    const div = document.createElement('div');
    const cls = classify(msg);
    div.className = `log-entry ${cls}`.trim();
    div.innerHTML = `<span class="ts">[${time}]</span><span class="msg"></span>`;
    div.querySelector('.msg').textContent = String(msg);
    logEl.appendChild(div);
    // keep log size under control
    const max = 500;
    while (logEl.children.length > max){
      logEl.removeChild(logEl.firstChild);
    }
    logEl.scrollTop = logEl.scrollHeight;
  }

  async function sendCommand(text){
    if (!text || !text.trim()) return;
    log(`You: ${text}`);
    try {
      window.BittuUI.setProcessing();
      if (sendBtn) sendBtn.disabled = true;
      const res = await fetch('http://127.0.0.1:8008/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      if (!res.ok) throw new Error('Request failed');
      const data = await res.json();
      if (data && data.response) {
        log(`Bittu: ${data.response}`);
      }
    } catch (e) {
      log(`Error submitting command: ${e.message || e}`);
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      window.BittuUI.setListening();
    }
  }

  function setStatusDots(){
    if (!dotListening || !dotProcessing || !dotSpeaking) return;
    dotListening.classList.toggle('active', state.mode === 'listening');
    dotProcessing.classList.toggle('active', state.mode === 'processing');
    dotSpeaking.classList.toggle('active', state.mode === 'speaking');
    if (statusBar){
      const m = state.mode;
      const text = m === 'listening' ? 'Listening' : m === 'processing' ? 'Processing' : m === 'speaking' ? 'Speaking' : 'Idle';
      statusBar.textContent = `Status: ${text}`;
    }
  }

  // Server heartbeat to enrich statusBar
  async function heartbeat(){
    try {
      const res = await fetch('http://127.0.0.1:8008/health', { cache: 'no-store' });
      const ok = res.ok;
      if (statusBar){
        const m = state.mode;
        const text = m === 'listening' ? 'Listening' : m === 'processing' ? 'Processing' : m === 'speaking' ? 'Speaking' : 'Idle';
        statusBar.textContent = `Status: ${text} · Server: ${ok ? 'OK' : 'Down'}`;
      }
    } catch(_){
      if (statusBar){
        const m = state.mode;
        const text = m === 'listening' ? 'Listening' : m === 'processing' ? 'Processing' : m === 'speaking' ? 'Speaking' : 'Idle';
        statusBar.textContent = `Status: ${text} · Server: Down`;
      }
    } finally {
      setTimeout(heartbeat, 5000);
    }
  }

  function initGraph(){
    if (!canvas || !ctx) return;
    const w = canvas.width, h = canvas.height;
    // Define bilateral cluster centers approximating cortical regions
    state.clusters = [];
    const left = [
      {x:w*0.33, y:h*0.35}, {x:w*0.28, y:h*0.50}, {x:w*0.35, y:h*0.65}
    ];
    const right = [
      {x:w*0.67, y:h*0.35}, {x:w*0.72, y:h*0.50}, {x:w*0.65, y:h*0.65}
    ];
    state.clusters = left.concat(right).map((c, i)=>({ ...c, id:i, hue: clusterHues[i % clusterHues.length] }));

    // Populate neurons around clusters with organic jitter
    state.nodes = [];
    for (const c of state.clusters){
      const localCount = 26;
      for (let i=0;i<localCount;i++){
        const ang = Math.random()*Math.PI*2;
        const rad = 18 + Math.random()*42;
        const jitter = (Math.sin(i*2.13)+Math.cos(i*3.7))*2;
        const x = c.x + Math.cos(ang)*(rad+jitter);
        const y = c.y + Math.sin(ang)*(rad-jitter);
        const r = 3 + Math.random()*2.5;
        state.nodes.push({x, y, baseR:r, clusterId: c.id, hue: c.hue});
      }
    }

    // Create axon bézier curves across and within hemispheres
    state.axons = [];
    const all = state.clusters;
    function bez(p0,p1,scale){
      const mx = (p0.x+p1.x)/2, my=(p0.y+p1.y)/2;
      const nx = p1.y-p0.y, ny = -(p1.x-p0.x);
      const len = Math.hypot(nx,ny)||1;
      const ux = nx/len, uy=ny/len;
      const s = scale*(0.2+Math.random()*0.8);
      const hue = Math.round(((p0.hue || 160) + (p1.hue || 160))/2);
      return {p0, p1, c0:{x: mx+ux*s, y: my+uy*s}, c1:{x: mx-ux*s, y: my-uy*s}, hue};
    }
    for (let i=0;i<all.length;i++){
      for (let j=i+1;j<all.length;j++){
        const p0 = all[i], p1 = all[j];
        const d = Math.hypot(p1.x-p0.x, p1.y-p0.y);
        if (d> w*0.42) continue;
        if (Math.random()<0.55){
          state.axons.push(bez(p0,p1, d*0.35));
        }
      }
    }

    // Seed signals along axons
    state.packets = [];
    for (let p=0;p<46;p++){
      const ax = state.axons[Math.floor(Math.random()*state.axons.length)];
      state.packets.push({axon: ax, t: Math.random(), speed: 0.002 + Math.random()*0.005});
    }

    // Initial layout
    updateLayout();

    // Floating orbs
    state.orbs = [];
    for (let k=0;k<12;k++){
      state.orbs.push({
        x: Math.random()*w,
        y: Math.random()*h,
        r: 8 + Math.random()*14,
        dx: (Math.random()*2-1)*0.2,
        dy: (Math.random()*2-1)*0.2,
        hue: 120 + Math.random()*120
      });
    }
  }

  function computeBounds(){
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    const includePoint = (pt)=>{ if (!pt) return; if (pt.x<minX) minX=pt.x; if (pt.y<minY) minY=pt.y; if (pt.x>maxX) maxX=pt.x; if (pt.y>maxY) maxY=pt.y; };
    for (const n of state.nodes) includePoint(n);
    for (const a of state.axons){ includePoint(a.p0); includePoint(a.p1); includePoint(a.c0); includePoint(a.c1); }
    if (minX===Infinity) return null;
    return { minX, minY, maxX, maxY, width: maxX-minX, height: maxY-minY, cx: (minX+maxX)/2, cy: (minY+maxY)/2 };
  }

  function updateLayout(){
    if (!canvas) return;
    const b = computeBounds();
    if (!b) { state.offset.x=0; state.offset.y=0; state.scale=1; return; }
    const pad = 0.88; // fit factor
    const sx = (canvas.width*pad) / (b.width || 1);
    const sy = (canvas.height*pad) / (b.height || 1);
    state.scale = Math.max(0.5, Math.min(sx, sy));
    const w2 = canvas.width/2, h2 = canvas.height/2;
    state.offset.x = w2 - b.cx*state.scale;
    state.offset.y = h2 - b.cy*state.scale;
  }

  function clear(){
    if (!ctx) return;
    ctx.clearRect(0,0,canvas.width, canvas.height);
  }

  function drawBrainOutline(){
    if (!ctx) return;
    // Intentionally left blank: no silhouette, only network
  }

  function drawAxons(){
    if (!ctx) return;
    ctx.save();
    ctx.translate(state.offset.x, state.offset.y);
    ctx.scale(state.scale, state.scale);
    for (const a of state.axons){
      // Base hue per axon with subtle state tint
      let baseHue = a.hue || 160;
      let tint = 0;
      if (state.mode==='speaking') tint = -10; else if (state.mode==='processing') tint = +20; else if (state.mode==='listening') tint = +0;
      const hue = (baseHue + tint + 360) % 360;
      const pulse = (Math.sin(state.t*0.03)+1)/2;
      const alpha = state.mode==='idle' ? 0.06 : 0.12 + pulse*0.2;
      ctx.strokeStyle = `hsla(${hue}, 95%, 62%, ${alpha})`;
      ctx.lineWidth = 1.0 + pulse*0.7;
      ctx.beginPath();
      ctx.moveTo(a.p0.x, a.p0.y);
      ctx.bezierCurveTo(a.c0.x, a.c0.y, a.c1.x, a.c1.y, a.p1.x, a.p1.y);
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawNodes(){
    if (!ctx) return;
    ctx.save();
    ctx.translate(state.offset.x, state.offset.y);
    ctx.scale(state.scale, state.scale);
    for (let i=0;i<state.nodes.length;i++){
      const n = state.nodes[i];
      const pulse = (Math.sin(state.t*0.06 + i*0.7)+1)/2;
      const r = n.baseR * (0.9 + pulse*0.8);
      // Cluster-driven color with state tint
      const baseHue = n.hue || 160;
      let tint = 0;
      if (state.mode==='speaking') tint = -10; else if (state.mode==='processing') tint = +20; else if (state.mode==='listening') tint = +0;
      const hue = (baseHue + tint + 360) % 360;
      const glow = state.mode==='idle' ? 0.06 : 0.30 + pulse*0.46;
      // core
      const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, r+6);
      grad.addColorStop(0, `hsla(${hue}, 92%, ${state.mode==='idle'?80:88}%, 1)`);
      grad.addColorStop(0.7, `hsla(${hue}, 85%, 58%, 0.28)`);
      grad.addColorStop(1, `hsla(${hue}, 80%, 54%, 0.16)`);
      ctx.fillStyle = grad;
      ctx.shadowColor = `hsla(${hue}, 100%, 65%, ${glow})`;
      ctx.shadowBlur = 22 + pulse*26;
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI*2);
      ctx.fill();
      // subtle outline for structure
      ctx.lineWidth = 0.6;
      ctx.strokeStyle = `hsla(${hue}, 80%, 70%, 0.15)`;
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawPackets(){
    if (!ctx) return;
    ctx.save();
    ctx.translate(state.offset.x, state.offset.y);
    ctx.scale(state.scale, state.scale);
    for (const p of state.packets){
      const a = p.axon;
      // cubic bezier interpolation
      const t = p.t;
      const x = Math.pow(1-t,3)*a.p0.x + 3*Math.pow(1-t,2)*t*a.c0.x + 3*(1-t)*t*t*a.c1.x + t*t*t*a.p1.x;
      const y = Math.pow(1-t,3)*a.p0.y + 3*Math.pow(1-t,2)*t*a.c0.y + 3*(1-t)*t*t*a.c1.y + t*t*t*a.p1.y;
      // Use axon's hue for packet color with brightness bump during processing
      const baseHue = a.hue || 160;
      const hue = (baseHue + (state.mode==='processing'? 10 : 0)) % 360;
      ctx.fillStyle = `hsla(${hue}, 96%, 78%, 0.98)`;
      ctx.beginPath();
      ctx.arc(x, y, 1.8, 0, Math.PI*2);
      ctx.fill();
    }
    ctx.restore();
  }

  function drawOrbs(){
    if (!ctx) return;
    // Intentionally blank: no decorative orbs
  }

  function animate(){
    if (!ctx) return;
    state.t += 1;
    // Recompute layout in case canvas size changed
    updateLayout();
    clear();
    // Only the network
    drawAxons();
    drawNodes();
    // no orbs
    // advance packets
    for (const p of state.packets){
      p.t += p.speed * (state.mode==='processing' ? 2.0 : 1.1);
      if (p.t > 1){
        p.t = 0;
        // switch axon randomly
        p.axon = state.axons[Math.floor(Math.random()*state.axons.length)] || p.axon;
      }
    }
    drawPackets();
    requestAnimationFrame(animate);
  }

  // Public API for toggling states from host app
  window.BittuUI = {
    setIdle(){ state.mode='idle'; setStatusDots(); log('State: idle'); },
    setListening(){ state.mode='listening'; setStatusDots(); log('State: listening'); },
    setProcessing(){ state.mode='processing'; setStatusDots(); log('State: processing'); },
    setSpeaking(){ state.mode='speaking'; setStatusDots(); log('State: speaking'); },
    heard(text){ log(`Heard: ${text}`); this.setProcessing(); },
    responded(text){ log(`Bittu: ${text}`); this.setSpeaking(); setTimeout(()=>this.setListening(), 800); }
  };

  // Auto-subscribe to local SSE if available (http://127.0.0.1:8008/events)
  function subscribeSSE(){
    try {
      const src = new EventSource('http://127.0.0.1:8008/events');
      src.addEventListener('heard', e => {
        try { const d = JSON.parse(e.data); BittuUI.heard(d.text || ''); } catch(_){}
      });
      src.addEventListener('processing', () => { BittuUI.setProcessing(); });
      src.addEventListener('speaking', e => {
        try { const d = JSON.parse(e.data); BittuUI.responded(d.text || ''); } catch(_){}
      });
      src.addEventListener('listening', () => { BittuUI.setListening(); });
      src.addEventListener('log', e => {
        try { const d = JSON.parse(e.data); if (d && d.message) log(String(d.message)); } catch(_){ }
      });
      src.onerror = () => { /* ignore to keep page working without server */ };
    } catch (err) {
      // silently ignore
    }
  }

  // Boot
  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', () => {
      initGraph(); setStatusDots(); animate();
      window.BittuUI.setIdle();
      subscribeSSE();
      heartbeat();
      if (cmdInput && sendBtn){
        const handler = () => { const val = cmdInput.value; cmdInput.value=''; sendCommand(val); };
        sendBtn.addEventListener('click', handler);
        cmdInput.addEventListener('keydown', (e)=>{ if (e.key==='Enter'){ handler(); } });
      }
      if (clearLogBtn) clearLogBtn.addEventListener('click', ()=>{ if (logEl) logEl.innerHTML=''; });
      if (popoutBtn) popoutBtn.addEventListener('click', ()=>{ window.open(window.location.href, '_blank'); });
    });
  } else {
    initGraph(); setStatusDots(); animate();
    window.BittuUI.setIdle();
    subscribeSSE();
    heartbeat();
    if (cmdInput && sendBtn){
      const handler = () => { const val = cmdInput.value; cmdInput.value=''; sendCommand(val); };
      sendBtn.addEventListener('click', handler);
      cmdInput.addEventListener('keydown', (e)=>{ if (e.key==='Enter'){ handler(); } });
    }
    if (clearLogBtn) clearLogBtn.addEventListener('click', ()=>{ if (logEl) logEl.innerHTML=''; });
    if (popoutBtn) popoutBtn.addEventListener('click', ()=>{ window.open(window.location.href, '_blank'); });
  }
})();
