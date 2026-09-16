(function(){
  var _rawFetch = window.fetch.bind(window);
  var SBTOK = null;

  // Recupere le jeton une seule fois, avec l'appel brut (non enveloppe).
  var SBTOK_READY = _rawFetch('/api/token')
    .then(function(r){ return r.json(); })
    .then(function(j){ SBTOK = j && j.token; return SBTOK; })
    .catch(function(){ return null; });

  window.fetch = async function(input, init){
    var url = (typeof input === 'string') ? input
            : (input && input.url) ? input.url : '';
    if(url.indexOf('/api/') !== 0 || url === '/api/token'){
      return _rawFetch(input, init);
    }
    if(!SBTOK){ await SBTOK_READY; }
    init = init || {};
    var h = new Headers(init.headers || {});
    if(SBTOK) h.set('X-Prisme-Token', SBTOK);
    init.headers = h;
    return _rawFetch(input, init);
  };
})();
