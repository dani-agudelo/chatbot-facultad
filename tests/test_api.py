"""Tests minimos de API y configuracion LLM."""

from __future__ import annotations

import sys
import unittest
from types import ModuleType
from unittest.mock import MagicMock, patch

import config
from fastapi.testclient import TestClient


def _install_fake_nvidia_llm_module() -> None:
    if "llama_index.llms.nvidia" not in sys.modules:
        fake_module = ModuleType("llama_index.llms.nvidia")
        fake_module.NVIDIA = MagicMock(name="NVIDIA")
        sys.modules["llama_index.llms.nvidia"] = fake_module


class LLMProviderTests(unittest.TestCase):
    def test_get_llm_provider_nvidia(self) -> None:
        _install_fake_nvidia_llm_module()

        with patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "nvidia",
                "NVIDIA_API_KEY": "nvapi-test-key",
            },
            clear=False,
        ):
            from importlib import reload

            import llm.nvidia_provider as nvidia_provider

            reload(nvidia_provider)

            from llm.factory import get_llm_provider

            provider = get_llm_provider()
            self.assertEqual(provider.get_provider_name(), "nvidia")

    def test_get_llm_provider_gemini(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "gemini",
                "GEMINI_API_KEY": "gemini-test-key",
                "NVIDIA_API_KEY": "nvapi-test-key",
            },
            clear=False,
        ):
            from llm.factory import get_llm_provider

            provider = get_llm_provider()
            self.assertEqual(provider.get_provider_name(), "gemini")


class APITests(unittest.TestCase):
    def setUp(self) -> None:
        config._CONFIGURED = False

    def tearDown(self) -> None:
        config._CONFIGURED = False

    def test_health_returns_ok_and_model(self) -> None:
        from api.main import app

        mock_provider = MagicMock()
        mock_provider.get_provider_name.return_value = "nvidia"

        with (
            patch("api.main.configure_settings"),
            patch("api.main.setup_logging"),
            patch("api.main.get_llm_provider", return_value=mock_provider),
            patch("api.main.get_active_llm_model", return_value="meta/llama-3.1-8b-instruct"),
        ):
            with TestClient(app) as client:
                response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["model"], "meta/llama-3.1-8b-instruct")

    def test_ingest_without_pdfs_returns_400(self) -> None:
        from api.main import app

        mock_provider = MagicMock()
        mock_provider.get_provider_name.return_value = "nvidia"

        with (
            patch("api.main.configure_settings"),
            patch("api.main.setup_logging"),
            patch("api.main.get_llm_provider", return_value=mock_provider),
            patch(
                "carga_documentos.pipeline.load_pdf_documents",
                side_effect=ValueError("No se encontraron documentos PDF en /tmp."),
            ),
        ):
            with TestClient(app) as client:
                response = client.post("/ingest")

        self.assertEqual(response.status_code, 400)
        self.assertIn("PDF", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
