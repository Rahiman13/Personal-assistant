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
    nodes: [],      // [{x,y,r,glow}]
    connections: [], // [{a,b,len}]
    packets: []     // flowing particles along edges
  };

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
    // Generate neurons (network cells)
    const count = 42;
    state.nodes = [];
    for (let i=0;i<count;i++){
      const x = w*0.1 + Math.random()*w*0.8;
      const y = h*0.15 + Math.random()*h*0.7;
      const r = 4 + Math.random()*3;
      state.nodes.push({x, y, baseR: r, glow: 0});
    }
    // Connect each node to its K nearest neighbors
    const K = 3;
    const connections = [];
    for (let i=0;i<state.nodes.length;i++){
      const dists = [];
      for (let j=0;j<state.nodes.length;j++){
        if (i===j) continue;
        const dx = state.nodes[j].x - state.nodes[i].x;
        const dy = state.nodes[j].y - state.nodes[i].y;
        dists.push({j, d: Math.hypot(dx,dy)});
      }
      dists.sort((a,b)=>a.d-b.d);
      for (let k=0;k<K;k++){
        const neighbor = dists[k];
        if (!neighbor) continue;
        const a = i, b = neighbor.j;
        if (a<b) connections.push({a,b,len: neighbor.d});
      }
    }
    // Remove duplicates
    const uniq = new Map();
    for (const c of connections){
      const key = c.a+"-"+c.b;
      if (!uniq.has(key)) uniq.set(key, c);
    }
    state.connections = Array.from(uniq.values());

    // Seed flowing packets
    state.packets = [];
    for (let p=0;p<30;p++){
      const edge = state.connections[Math.floor(Math.random()*state.connections.length)];
      state.packets.push({edge, t: Math.random(), speed: 0.002 + Math.random()*0.006});
    }
  }

  function clear(){
    if (!ctx) return;
    ctx.clearRect(0,0,canvas.width, canvas.height);
  }

  function drawBrainOutline(){
    if (!ctx) return;
    const w = canvas.width, h = canvas.height;
    ctx.save();
    ctx.fillStyle = 'rgba(10, 24, 22, 0.9)';
    ctx.strokeStyle = 'rgba(0, 255, 136, 0.2)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    // Simple organic shape
    ctx.moveTo(w*0.2, h*0.35);
    ctx.bezierCurveTo(w*0.25, h*0.15, w*0.45, h*0.10, w*0.50, h*0.20);
    ctx.bezierCurveTo(w*0.55, h*0.10, w*0.75, h*0.15, w*0.80, h*0.35);
    ctx.bezierCurveTo(w*0.85, h*0.55, w*0.75, h*0.75, w*0.55, h*0.78);
    ctx.bezierCurveTo(w*0.50, h*0.82, w*0.45, h*0.82, w*0.40, h*0.78);
    ctx.bezierCurveTo(w*0.25, h*0.75, w*0.15, h*0.55, w*0.2, h*0.35);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }

  function drawConnections(){
    if (!ctx) return;
    ctx.save();
    for (const c of state.connections){
      const n1 = state.nodes[c.a], n2 = state.nodes[c.b];
      let hue;
      if (state.mode==='listening') hue = 150;
      else if (state.mode==='speaking') hue = 30;
      else if (state.mode==='processing') hue = 200;
      else hue = 140;
      const pulse = (Math.sin(state.t*0.05 + c.len*0.02)+1)/2;
      const alpha = state.mode==='idle' ? 0.07 : 0.14 + pulse*0.2;
      ctx.strokeStyle = `hsla(${hue}, 90%, 60%, ${alpha})`;
      ctx.lineWidth = 0.8 + pulse*0.8;
      ctx.beginPath();
      ctx.moveTo(n1.x, n1.y);
      ctx.lineTo(n2.x, n2.y);
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawNodes(){
    if (!ctx) return;
    ctx.save();
    for (let i=0;i<state.nodes.length;i++){
      const n = state.nodes[i];
      const pulse = (Math.sin(state.t*0.06 + i*0.9)+1)/2; // 0..1
      const r = n.baseR * (0.9 + pulse*0.8);
      let hue;
      if (state.mode==='listening') hue = 150;
      else if (state.mode==='speaking') hue = 30;
      else if (state.mode==='processing') hue = 200;
      else hue = 140;
      const glow = state.mode==='idle' ? 0.06 : 0.22 + pulse*0.35;
      // core
      const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, r+6);
      grad.addColorStop(0, `hsla(${hue}, 95%, ${state.mode==='idle'?70:80}%, 0.95)`);
      grad.addColorStop(1, `hsla(${hue}, 80%, 50%, 0.15)`);
      ctx.fillStyle = grad;
      ctx.shadowColor = `hsla(${hue}, 100%, 65%, ${glow})`;
      ctx.shadowBlur = 14 + pulse*20;
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI*2);
      ctx.fill();
    }
    ctx.restore();
  }

  function drawPackets(){
    if (!ctx) return;
    ctx.save();
    for (const p of state.packets){
      const c = p.edge;
      const n1 = state.nodes[c.a], n2 = state.nodes[c.b];
      const x = n1.x + (n2.x - n1.x) * p.t;
      const y = n1.y + (n2.y - n1.y) * p.t;
      let hue;
      if (state.mode==='processing') hue = 200; else if (state.mode==='speaking') hue = 30; else hue = 150;
      ctx.fillStyle = `hsla(${hue}, 95%, 70%, 0.9)`;
      ctx.beginPath();
      ctx.arc(x, y, 1.6, 0, Math.PI*2);
      ctx.fill();
    }
    ctx.restore();
  }

  function animate(){
    if (!ctx) return;
    state.t += 1;
    clear();
    drawBrainOutline();
    drawConnections();
    drawNodes();
    // advance packets
    for (const p of state.packets){
      p.t += p.speed * (state.mode==='processing' ? 2.0 : 1.0);
      if (p.t > 1){
        p.t = 0;
        // switch edge randomly
        p.edge = state.connections[Math.floor(Math.random()*state.connections.length)] || p.edge;
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
