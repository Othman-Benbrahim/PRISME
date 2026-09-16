var ONB_PROVIDERS = [
  {id:'openrouter', label:'OpenRouter (accès à tous les modèles)', url:'https://openrouter.ai/api/v1',
   model:'openai/gpt-4o-mini', key:true, ph:'sk-or-v1-…',
   help:'Une seule clé pour GPT, Claude, Gemini, Llama. Créez-la sur openrouter.ai.'},
  {id:'openai', label:'OpenAI', url:'https://api.openai.com/v1',
   model:'gpt-4o-mini', key:true, ph:'sk-…', help:'Clé depuis platform.openai.com.'},
  {id:'fantasy', label:'FantasyAI', url:'https://fantasyai.cloud/api/v1',
   model:'gpt-4o', key:true, ph:'fantasy-…', help:''},
  {id:'ollama', label:'Ollama (local, gratuit)', url:'http://localhost:11434/v1',
   model:'llama3.1', key:false, ph:'',
   help:'Aucune clé. Ollama doit tourner sur votre machine (ollama serve).'},
  {id:'lmstudio', label:'LM Studio (local, gratuit)', url:'http://localhost:1234/v1',
   model:'', key:false, ph:'',
   help:'Aucune clé. Démarrez le serveur local dans LM Studio.'},
  {id:'anthropic', label:'Anthropic (Claude)', url:'https://api.anthropic.com/v1',
   model:'claude-sonnet-5', key:true, ph:'sk-ant-…',
   help:'Clé depuis console.anthropic.com. Dialecte propre à Anthropic, géré en interne.'},
  {id:'gemini', label:'Google Gemini', url:'https://generativelanguage.googleapis.com/v1beta/openai',
   model:'gemini-2.5-flash', key:true, ph:'AIza…',
   help:'Clé depuis Google AI Studio. Cliquez sur Tester pour charger la liste des modèles.'},
  {id:'grok', label:'xAI (Grok)', url:'https://api.x.ai/v1',
   model:'grok-4.6', key:true, ph:'xai-…',
   help:'Clé depuis console.x.ai.'},
  {id:'custom', label:'Autre (compatible OpenAI)', url:'', model:'', key:true, ph:'',
   help:'Tout service exposant /chat/completions au format OpenAI.'}
];

function onbCur(){
  var v = document.getElementById('onb-prov').value;
  for(var i=0;i<ONB_PROVIDERS.length;i++){ if(ONB_PROVIDERS[i].id===v) return ONB_PROVIDERS[i]; }
  return ONB_PROVIDERS[0];
}

function onbProv(){
  var p = onbCur();
  document.getElementById('onb-url').value = p.url;
  document.getElementById('onb-model').value = p.model;
  document.getElementById('onb-key').placeholder = p.ph;
  document.getElementById('onb-help').textContent = p.help;
  document.getElementById('onb-key-block').style.display = p.key ? 'block' : 'none';
  if(!p.key) document.getElementById('onb-key').value = '';
}

async function onbTest(){
  var st = document.getElementById('onb-status');
  st.style.color = 'var(--tx2)';
  st.textContent = '⏳ Test en cours…';
  await post('/api/config', {
    base_url: document.getElementById('onb-url').value.trim(),
    api_key:  document.getElementById('onb-key').value.trim(),
    model:    document.getElementById('onb-model').value.trim()
  });
  try {
    var r = await fetch('/api/test').then(function(r){ return r.json(); });
    if(r.ok){
      st.style.color = '#3aa655';
      st.textContent = '✓ Connexion établie.';
      var m = await fetch('/api/models').then(function(r){ return r.json(); });
      var list = (m.models || []).slice(0, 200);
      document.getElementById('onb-models').innerHTML =
        list.map(function(x){ return '<option value="' + x + '">'; }).join('');
      if(!document.getElementById('onb-model').value && list.length)
        document.getElementById('onb-model').value = list[0];
    } else {
      st.style.color = '#c0392b';
      st.textContent = '✗ ' + (r.error || ('HTTP ' + (r.status || '?')));
    }
  } catch(e){
    st.style.color = '#c0392b';
    st.textContent = '✗ ' + e;
  }
}

async function onbSave(){
  var st = document.getElementById('onb-status');
  var r = await post('/api/setup', {
    workspace: document.getElementById('onb-ws').value.trim(),
    base_url:  document.getElementById('onb-url').value.trim(),
    api_key:   document.getElementById('onb-key').value.trim(),
    model:     document.getElementById('onb-model').value.trim()
  });
  if(r.error){
    st.style.color = '#c0392b';
    st.textContent = '✗ ' + r.error;
    return;
  }
  location.reload();
}

window.addEventListener('load', async function(){
  try {
    var s = await fetch('/api/setup/state').then(function(r){ return r.json(); });
    if(s.configured) return;
    document.getElementById('onb-prov').innerHTML = ONB_PROVIDERS.map(function(p){
      return '<option value="' + p.id + '">' + p.label + '</option>';
    }).join('');
    document.getElementById('onb-ws').value = s.suggested_workspace;
    onbProv();
    document.getElementById('monb').classList.add('on');
  } catch(e){ /* route absente : patch Python non applique */ }
});
