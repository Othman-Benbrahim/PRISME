import {pageTexte,verifierSortie} from './metier.js';
export async function demonstration(D,relever,_lireId,choisir){
 const id='d-'+crypto.randomUUID();await D.creer({id,question:'[DÉMONSTRATION FICTIVE] Le service Alpha sera-t-il rétabli ?',perimetre:'Trois pièces fabriquées pour le test visuel',horizon:'Scénario fictif',decision:'Tester Constat intégré, sans décision réelle'});choisir(id);
 const textes=[
 'Document fictif de démonstration. Le service Alpha ne répond plus depuis le matin. Le technicien annonce : « Nous examinons la panne et publierons un compte rendu. » Aucun rétablissement n’est observé dans cette pièce. Le document est fabriqué pour tester les fonctions du logiciel.',
 'Document fictif de démonstration. Une opération de maintenance est annoncée sur le service Alpha. Le responsable déclare : « Le diagnostic doit précéder la remise en service. » Cette déclaration ne permet pas de conclure que le service a déjà été réparé. Aucun événement réel n’est décrit.',
 'Document fictif de démonstration. Un essai du service Alpha renvoie une erreur. Plusieurs explications restent possibles : panne réseau, maintenance ou incident matériel. Ce compte rendu ne tranche pas entre les causes. Il constitue uniquement une pièce pour essayer la matrice ACH.'
 ];
 for(let i=0;i<textes.length;i++)await D.verser(id,pageTexte({titre:'Pièce fictive '+(i+1),texte:textes[i],url:`https://demo-${i+1}.invalid/alpha`,editeur:`Éditeur fictif ${i+1}`}));
 await relever();const sources=await D.corpus(id),releve=(await D.relevés(id)).at(-1);
 const brut={hypotheses:[{id:'H1',role:'dominante',enonce:'Le service Alpha sera rétabli après la maintenance',confirmerait:'Un test observe une réponse correcte',demolirait:'Un test après maintenance échoue'},
 {id:'H2',role:'dissidente',enonce:'Un incident matériel empêchera la remise en service',confirmerait:'Une pièce matérielle est déclarée défaillante',demolirait:'Le service fonctionne sans remplacement'},
 {id:'H3',role:'fractale',enonce:'La panne affecte aussi des services voisins',confirmerait:'Des tests sur des services voisins échouent',demolirait:'Tous les services voisins répondent'}],
 preuves:sources.map((s,i)=>({id:'P'+(i+1),enonce:'Observation fictive décrite dans '+s.titre,sources:[s.id],passages:[{source:s.id,extrait:s.texte.split('. ')[1]+'.'}]})),
 matrice:{P1:{H1:'C',H2:'C',H3:'N'},P2:{H1:'C',H2:'N',H3:'N'},P3:{H1:'N',H2:'C',H3:'N'}}};
 const v=verifierSortie(5,brut,sources,{});await D.ajouter(id,{t:'etape',numero:5,nom:'ACH fictive — démonstration',parents:{},releveRef:releve.empreinteCorpus,
 reference:'ach-heuer.md',modele:'aucun',fournisseur:'jeu de démonstration fabriqué',brut:JSON.stringify(brut,null,2),...v,validee:false});return id;
}
