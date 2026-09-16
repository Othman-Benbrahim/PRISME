var AISTREAM = {ctrl:null, t0:0, timer:null};

function aiStreamShow(){
  AISTREAM.t0 = Date.now();
  document.getElementById('aistream-body').textContent = '';
  document.getElementById('aistream-count').textContent = '0 caractère';
  document.getElementById('aistream-time').textContent = '0 s';
  document.getElementById('aistream').classList.add('on');
  clearInterval(AISTREAM.timer);
  AISTREAM.timer = setInterval(function(){
    document.getElementById('aistream-time').textContent =
      Math.round((Date.now() - AISTREAM.t0) / 1000) + ' s';
  }, 1000);
}

function aiStreamHide(){
  clearInterval(AISTREAM.timer);
  document.getElementById('aistream').classList.remove('on');
  AISTREAM.ctrl = null;
}

function aiStreamAbort(){
  if(AISTREAM.ctrl) AISTREAM.ctrl.abort();
  aiStreamHide();
}

async function aiStreamCall(data){
  var ctrl = new AbortController();
  AISTREAM.ctrl = ctrl;
  aiStreamShow();

  var resp;
  try {
    resp = await fetch('/api/ai/stream', {
      method : 'POST',
      headers: {'Content-Type': 'application/json'},
      body   : JSON.stringify(data),
      signal : ctrl.signal
    });
  } catch(e){
    aiStreamHide();
    if(e.name === 'AbortError') return {error: 'Interrompu'};
    return null;                       // repli sur la route classique
  }

  if(!resp.ok || !resp.body){
    aiStreamHide();
    if(resp.status === 400){
      try { return await resp.json(); } catch(e){ return {error: 'HTTP 400'}; }
    }
    return null;                       // repli
  }

  var reader  = resp.body.getReader();
  var decoder = new TextDecoder();
  var buf = '', full = '', err = null;
  var bodyEl  = document.getElementById('aistream-body');
  var countEl = document.getElementById('aistream-count');

  try {
    while(true){
      var res = await reader.read();
      if(res.done) break;
      buf += decoder.decode(res.value, {stream:true});
      var lines = buf.split('\n');
      buf = lines.pop();
      for(var i=0;i<lines.length;i++){
        var line = lines[i].trim();
        if(!line || line.indexOf('data:') !== 0) continue;
        var obj;
        try { obj = JSON.parse(line.slice(5).trim()); } catch(e){ continue; }
        if(obj.error){ err = obj.error; }
        else if(obj.delta){
          full += obj.delta;
          bodyEl.textContent = full.length > 1200 ? '…' + full.slice(-1200) : full;
          bodyEl.scrollTop = bodyEl.scrollHeight;
          countEl.textContent = full.length + ' caractères';
        }
      }
    }
  } catch(e){
    aiStreamHide();
    if(e.name === 'AbortError') return {error: 'Interrompu'};
    return full ? {response: full} : null;
  }

  aiStreamHide();
  if(err)   return {error: err};
  if(!full) return null;               // rien recu : repli
  return {response: full};
}

// Enveloppe post() : seul '/api/ai' est dérouté, tout le reste est intact.
// Tentée tout de suite ET au chargement : ce bloc peut être inséré avant ou
// après la définition de post(), l'enveloppe s'applique dans les deux cas.
function aiStreamWrapPost(){
  if(typeof post !== 'function' || post.__sbStream) return false;
  var _origPost = post;
  var wrapped = async function(url, data){
    if(url !== '/api/ai') return _origPost(url, data);
    var r = await aiStreamCall(data);
    if(r) return r;
    return _origPost(url, data);       // repli silencieux
  };
  wrapped.__sbStream = true;
  post = wrapped;
  return true;
}
if(!aiStreamWrapPost()){
  window.addEventListener('load', aiStreamWrapPost);
}
