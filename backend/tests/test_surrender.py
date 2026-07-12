import unittest

from backend.main import build_surrender_payload


class SurrenderPayloadTests(unittest.TestCase):
    def test_build_surrender_payload_marks_opponent_as_winner(self):
        room = {
            "board": [[0, 0], [0, 0]],
            "turn": 1,
        }

        payload = build_surrender_payload(room, 1)

        self.assertTrue(payload["game_over"])
        self.assertEqual(payload["turn"], 2)
        self.assertIn("降参", payload["message"])
        self.assertIn("勝ち", payload["message"])


if __name__ == "__main__":
    unittest.main()
