import os
import tempfile
import unittest

from backend import quiz_data


class QuizCategoryDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_quiz_root = quiz_data.QUIZ_ROOT
        self.addCleanup(setattr, quiz_data, "QUIZ_ROOT", self.original_quiz_root)
        quiz_data.QUIZ_ROOT = self.temp_dir.name

    def _write_question(self, category_dir, difficulty_dir, filename, question="Question"):
        path = os.path.join(category_dir, difficulty_dir, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(
                "{" \
                f'"Question": "{question}", '
                '"Options": ["A", "B"], '
                '"Answer": "A"' \
                "}"
            )

    def test_load_quiz_bank_only_includes_categories_that_meet_thresholds(self):
        alpha_dir = os.path.join(self.temp_dir.name, "Alpha")
        beta_dir = os.path.join(self.temp_dir.name, "Beta")

        for difficulty in ["Easy", "Normal", "Hard"]:
            os.makedirs(os.path.join(alpha_dir, difficulty), exist_ok=True)
            os.makedirs(os.path.join(beta_dir, difficulty), exist_ok=True)

        for index in range(8):
            self._write_question(alpha_dir, "Easy", f"{index + 1:02d}.json", f"Alpha easy {index}")
        for index in range(20):
            self._write_question(alpha_dir, "Normal", f"{index + 1:02d}.json", f"Alpha normal {index}")
        for index in range(4):
            self._write_question(alpha_dir, "Hard", f"{index + 1:02d}.json", f"Alpha hard {index}")

        for index in range(7):
            self._write_question(beta_dir, "Easy", f"{index + 1:02d}.json", f"Beta easy {index}")
        for index in range(19):
            self._write_question(beta_dir, "Normal", f"{index + 1:02d}.json", f"Beta normal {index}")
        for index in range(3):
            self._write_question(beta_dir, "Hard", f"{index + 1:02d}.json", f"Beta hard {index}")

        bank = quiz_data.load_quiz_bank(self.temp_dir.name)

        self.assertEqual(list(bank.keys()), ["Alpha"])
        self.assertEqual(len(bank["Alpha"]["easy"]), 8)
        self.assertEqual(len(bank["Alpha"]["normal"]), 20)
        self.assertEqual(len(bank["Alpha"]["hard"]), 4)


if __name__ == "__main__":
    unittest.main()
