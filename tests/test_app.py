# -*- coding: utf-8 -*-
"""zhwordgacha の unittest。ネットワークへの実アクセスは行わない。"""

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import WORDS, app  # noqa: E402


class ZhWordGachaTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(self.db_path)  # アプリ側に新規作成させる
        self._old_db = app.config["DATABASE"]
        app.config["DATABASE"] = self.db_path
        app.config["TESTING"] = True
        self.client = app.test_client()

    def tearDown(self):
        app.config["DATABASE"] = self._old_db
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _history_rows(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM history ORDER BY id").fetchall()
        conn.close()
        return rows

    def test_healthz(self):
        res = self.client.get("/healthz")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), {"status": "ok"})

    def test_index_ok(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("中国語単語ガチャ", res.get_data(as_text=True))

    def test_draw_returns_a_word(self):
        res = self.client.post("/draw")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        rows = self._history_rows()
        self.assertEqual(len(rows), 1)
        # 保存された単語がそのまま画面に出ていること
        self.assertIn(rows[0]["hanzi"], body)
        self.assertIn(rows[0]["pinyin"], body)
        self.assertIn(rows[0]["meaning"], body)
        self.assertIn(rows[0]["example_cn"], body)

    def test_draw_saves_history(self):
        self.client.post("/draw")
        rows = self._history_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        for key in ("drawn_on", "drawn_at", "hanzi", "pinyin",
                    "meaning", "example_cn", "example_jp"):
            self.assertTrue(row[key], key)

    def test_multiple_draws_same_day_allowed(self):
        for _ in range(3):
            res = self.client.post("/draw")
            self.assertEqual(res.status_code, 200)
        rows = self._history_rows()
        self.assertEqual(len(rows), 3)
        # 全部同じ日付（今日）で記録されている
        self.assertEqual(len({r["drawn_on"] for r in rows}), 1)

    def test_today_words_shown_on_index(self):
        self.client.post("/draw")
        rows = self._history_rows()
        res = self.client.get("/")
        body = res.get_data(as_text=True)
        self.assertIn("今日引いた単語", body)
        self.assertIn(rows[0]["hanzi"], body)

    def test_history_page_lists_draws(self):
        self.client.post("/draw")
        self.client.post("/draw")
        rows = self._history_rows()
        res = self.client.get("/history")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        for row in rows:
            self.assertIn(row["hanzi"], body)
            self.assertIn(row["example_cn"], body)

    def test_history_page_empty_ok(self):
        res = self.client.get("/history")
        self.assertEqual(res.status_code, 200)
        self.assertIn("まだ履歴がありません", res.get_data(as_text=True))

    def test_word_data_fields(self):
        # 語数は 80〜120 の範囲
        self.assertGreaterEqual(len(WORDS), 80)
        self.assertLessEqual(len(WORDS), 120)
        seen = set()
        for word in WORDS:
            for key in ("hanzi", "pinyin", "meaning", "example_cn", "example_jp"):
                self.assertIn(key, word)
                self.assertIsInstance(word[key], str)
                self.assertTrue(word[key].strip(), (word.get("hanzi"), key))
            # 例文にはその単語自体が含まれていること（学習用として最低限の整合）
            self.assertIn(word["hanzi"], word["example_cn"], word["hanzi"])
            seen.add(word["hanzi"])
        # 単語の重複がないこと
        self.assertEqual(len(seen), len(WORDS))


if __name__ == "__main__":
    unittest.main()
