"""Fabrique un modele ONNX minuscule et son tokeniseur, pour les tests.

Telecharger un vrai e5 (120 Mo) dans une suite de tests n'a pas de sens. Ce modele-ci
est un simple Gather : chaque jeton a un vecteur appris, et les jetons d'un meme theme
partagent une direction. Il suffit a verifier toute la chaine — tokenisation,
inference, moyenne masquee, normalisation, roles — sans rien telecharger.

Utilisable a la main :  python tests/fixtures/modele_minuscule.py /tmp/modele
"""
import json
import sys
from pathlib import Path

VOCAB = 64
DIM = 16
SPECIAUX = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "query", "passage", ":"]
THEME_A = "prediction horizon anticiper echeance calibrer prospective bascule signal prevoir".split()
THEME_B = "oignon huile olive plat cuisine recette poele sel poivre".split()


def disponible():
    try:
        import onnx           # noqa: F401
        import tokenizers     # noqa: F401
        return True
    except ImportError:
        return False


def construire(dossier):
    """Ecrit model.onnx, tokenizer.json et config.json dans `dossier`."""
    import numpy as np
    import onnx
    from onnx import TensorProto, helper, numpy_helper
    from tokenizers import Tokenizer, models, pre_tokenizers

    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)

    # Vocabulaire : chaque mot son identifiant, sans collision. Une collision rend deux
    # mots indiscernables et fausse tout, en silence.
    vocab, prochain = {}, 0
    for mot in SPECIAUX + THEME_A + THEME_B:
        if mot not in vocab:
            vocab[mot] = prochain
            prochain += 1
    while prochain < VOCAB:
        vocab["m%d" % prochain] = prochain
        prochain += 1
    assert len(set(vocab.values())) == len(vocab), "identifiants de jetons en double"

    rng = np.random.default_rng(3)
    table = rng.normal(0, 0.3, (VOCAB, DIM)).astype(np.float32)
    for theme in (THEME_A, THEME_B):
        base = rng.normal(0, 1, DIM).astype(np.float32)
        for mot in theme:
            table[vocab[mot]] = base + rng.normal(0, 0.15, DIM).astype(np.float32)

    noeud = helper.make_node("Gather", inputs=["table", "input_ids"], outputs=["sortie"], axis=0)
    graphe = helper.make_graph(
        [noeud], "minuscule",
        inputs=[helper.make_tensor_value_info("input_ids", TensorProto.INT64, ["lot", "len"]),
                helper.make_tensor_value_info("attention_mask", TensorProto.INT64, ["lot", "len"])],
        outputs=[helper.make_tensor_value_info("sortie", TensorProto.FLOAT, ["lot", "len", DIM])],
        initializer=[numpy_helper.from_array(table, name="table")])
    modele = helper.make_model(graphe, opset_imports=[helper.make_opsetid("", 13)])
    modele.ir_version = 9
    onnx.checker.check_model(modele)
    onnx.save(modele, str(dossier / "model.onnx"))

    tok = Tokenizer(models.WordPiece(vocab=vocab, unk_token="[UNK]", max_input_chars_per_word=64))
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    tok.save(str(dossier / "tokenizer.json"))

    (dossier / "config.json").write_text(
        json.dumps({"hidden_size": DIM, "architectures": ["Minuscule"]}), encoding="utf-8")
    return dossier


if __name__ == "__main__":
    cible = construire(sys.argv[1] if len(sys.argv) > 1 else "/tmp/modele-minuscule")
    print("modèle écrit dans", cible)
