// Contrat de versement, sans navigateur ni réseau. Aucun calcul de calibration.
const ligne = (v, nom, max = 4000) => {
  if (typeof v !== 'string') throw new Error(`${nom} : texte attendu`);
  const s = v.replace(/\s+/g, ' ').trim();
  if (!s || s.length > max) throw new Error(`${nom} : 1 à ${max} caractères attendus`);
  return s;
};
export function probabilite(v) {
  if (typeof v !== 'number' && typeof v !== 'string') throw new Error('Probabilité requise');
  if (typeof v === 'string' && !/^(?:0(?:\.\d+)?|1(?:\.0+)?)$/.test(v.trim())) {
    throw new Error('Probabilité entre 0 et 1, avec un point décimal');
  }
  const p = Number(v);
  if (!Number.isFinite(p) || p < 0 || p > 1) throw new Error('Probabilité entre 0 et 1');
  return p;
}
export function datePrisme(v) {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v)) throw new Error('Date butoir requise : AAAA-MM-JJ');
  const d = new Date(`${v}T00:00:00Z`);
  if (v.startsWith('0000-') || !Number.isFinite(d.getTime()) || d.toISOString().slice(0, 10) !== v) throw new Error('Date butoir impossible');
  return v;
}
export function preparerPrediction({ dossier, etape, hypotheseId, saisie }) {
  if (!dossier?.id || etape?.numero !== 5 || !etape.validee || !etape.complet) {
    throw new Error('Une étape ACH complète et validée est requise');
  }
  const h = etape.sortie?.hypotheses?.find(x => x.id === hypotheseId);
  if (!h) throw new Error('Hypothèse introuvable dans cette révision ACH');
  const champs = {
    enonce: ligne(saisie.enonce, 'Énoncé'),
    probabilite: probabilite(saisie.probabilite),
    echeance: datePrisme(saisie.echeance),
    critere_resolution: ligne(saisie.critere_resolution, 'Condition de résolution'),
    hypothese: ligne(`constat:${dossier.id}:${etape.ts}:${h.id}`, 'Référence ACH'),
    statut: 'ouverte',
  };
  if (saisie.domaine?.trim()) champs.domaine = ligne(saisie.domaine, 'Domaine');
  const preuves = etape.sortie.preuves || [];
  const sources = [...new Set(preuves.flatMap(p => p.sources || []))];
  const motif = ligne(`Constat — dossier ${dossier.id} ; question : ${dossier.question} ; ACH ${etape.ts} validée le ${etape.valideeLe}; corpus ${etape.releveRef}; hypothèse ${h.id} (${h.role}) : ${h.enonce} ; confirmerait : ${h.confirmerait} ; réfuterait : ${h.demolirait} ; sources du dossier : ${sources.join(', ')}. Probabilité, date butoir et condition de résolution saisies par l’auteur.`, 'Contexte ACH');
  return { type: 'prediction', titre: ligne(saisie.titre, 'Titre', 200), champs, motif };
}
