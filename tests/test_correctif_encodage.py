"""Correctif : les reponses IA sans charset declare etaient decodees en ISO-8859-1."""
import io
import json
import unittest
from unittest import mock

import requests

from commun import reset_vault

from prisme_core import config, providers
from prisme_core.app import create_app
from prisme_core.routes import ai, security

TEXTE = "Création d'un lien vers « référence » — déjà prêt"


def fake_response(body, content_type):
    r = requests.models.Response()
    r.status_code = 200
    r.headers["Content-Type"] = content_type
    r.raw = io.BytesIO(body.encode("utf-8"))
    return r


class TestEncodage(unittest.TestCase):
    def setUp(self):
        reset_vault()
        config.wr_cfg({"base_url": "http://localhost:11434/v1", "model": "m", "api_key": ""})

    def test_flux_sans_charset(self):
        sse = "".join("data: " + json.dumps({"choices": [{"delta": {"content": c}}]}) + "\n\n"
                      for c in (TEXTE[:10], TEXTE[10:])) + "data: [DONE]\n\n"
        with mock.patch.object(ai.http, "post", return_value=fake_response(sse, "text/event-stream")):
            c = create_app(with_plugins=False).test_client()
            body = c.post("/api/ai/stream", headers={"X-Prisme-Token": security.TOKEN},
                          json={"messages": [{"role": "user", "content": "x"}]}).get_data(as_text=True)
        pieces = [json.loads(line[5:]) for line in body.splitlines() if line.startswith("data:")]
        self.assertEqual("".join(p.get("delta", "") for p in pieces), TEXTE)

    def test_reponse_simple_sans_charset(self):
        payload = json.dumps({"choices": [{"message": {"content": TEXTE}}]}, ensure_ascii=False)
        with mock.patch.object(providers.http, "post", return_value=fake_response(payload, "text/plain")):
            text, err = providers._ai_call(config.rd_cfg(), [{"role": "user", "content": "x"}])
        self.assertIsNone(err)
        self.assertEqual(text, TEXTE)


if __name__ == "__main__":
    unittest.main()
