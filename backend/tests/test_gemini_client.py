import sys
import unittest
from pathlib import Path
from unittest.mock import patch, sentinel

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import gemini_client


class GeminiClientLifecycleTests(unittest.TestCase):
    def test_client_is_created_lazily_and_reused(self) -> None:
        gemini_client.get_gemini_client.cache_clear()
        self.addCleanup(gemini_client.get_gemini_client.cache_clear)

        with patch.object(
            gemini_client.genai,
            "Client",
            return_value=sentinel.client,
        ) as constructor:
            constructor.assert_not_called()

            first = gemini_client.get_gemini_client()
            second = gemini_client.get_gemini_client()

        self.assertIs(first, sentinel.client)
        self.assertIs(second, sentinel.client)
        constructor.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
