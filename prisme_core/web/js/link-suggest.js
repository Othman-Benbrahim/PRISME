// ══════════════════════════════════════════════════
//  SUGGESTIONS DE LIENS
// ══════════════════════════════════════════════════
async function suggestLinks(){
  if(!ACTIVE){toast('Ouvrez un fichier d\'abord');return;}
  var content=$('md-editor').value;
  var name=ACTIVE.split(/[/\\]/).pop().replace(/\.md$/i,'');
  var graphData=await fetch('/api/files/graph?dir='+eu(CUR_DIR)).then(function(r){return r.json();});
  var fileNames=(graphData.nodes||[]).map(function(n){return n.name;}).filter(function(n){return n!==name;});
  var cfg=await fetch('/api/config').then(function(r){return r.json();});
  toast('⏳ Analyse des liens possibles…',5000);
  var r=await post('/api/ai',{messages:[
    {role:'system',content:'Tu es expert en PKM (Personal Knowledge Management). Réponds UNIQUEMENT en JSON valide.'},
    {role:'user',content:'Fichier actuel : "'+name+'"\nFichiers disponibles : '+fileNames.slice(0,30).join(', ')+'\n\nContenu :\n'+content.slice(0,3000)+'\n\nIdentifie 3-5 passages qui mériteraient un [[wikilink]] vers un fichier existant.\nJSON : {"suggestions":[{"passage":"texte exact","link":"nom_fichier","reason":"pourquoi"}]}'}
  ],model:cfg.model});
  if(r.error){toast('⚠ '+r.error);return;}
  try{
    var jt=r.response,jm=jt.match(/\{[\s\S]*\}/);if(jm)jt=jm[0];
    var parsed=JSON.parse(jt); var suggs=parsed.suggestions||[];
    if(!suggs.length){toast('Aucune suggestion de lien trouvée');return;}
    var msg=suggs.map(function(s,i){return (i+1)+'. [['+s.link+']] → "'+s.passage.slice(0,50)+'"\n   '+s.reason;}).join('\n\n');
    alert('Suggestions de [[liens]] :\n\n'+msg+'\n\nCopiez les noms de fichiers et ajoutez [[nom]] manuellement dans l\'éditeur.');
  }catch(e){ toast('IA : '+r.response.slice(0,100)); }
}

