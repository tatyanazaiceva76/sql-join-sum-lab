"""Independent row-based reference and counterexamples for COUNT lab."""

import contextlib
import io
from pathlib import Path
import sqlite3
import unittest

import sql_count_lab as lab


def expected_by_sku(db):
    counts = {sku: 0 for (sku,) in db.execute("SELECT sku FROM products")}
    for sku, status in db.execute("SELECT sku, status FROM sales"):
        if status == "paid":
            counts[sku] += 1
    return sorted(counts.items())


class SQLCountLabTests(unittest.TestCase):
    def test_all_seven_scenarios(self):
        for name, changes, expected in lab.CASES:
            with self.subTest(name=name), contextlib.closing(lab.make_db(changes)) as db:
                self.assertEqual(db.execute(lab.CORRECT).fetchall(), expected)
                self.assertEqual(expected_by_sku(db), expected)
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_every_wrong_fix_has_a_counterexample(self):
        for label, query in lab.WRONG.items():
            with self.subTest(query=label):
                failures = []
                for name, changes, _ in lab.CASES:
                    with contextlib.closing(lab.make_db(changes)) as db:
                        if db.execute(query).fetchall() != expected_by_sku(db):
                            failures.append(name)
                self.assertTrue(failures, "Known wrong query escaped all fixtures")

    def test_cancelled_only_product_breaks_or_null_fix(self):
        with contextlib.closing(lab.make_db()) as db:
            self.assertEqual(db.execute(lab.WRONG["where_or_null"]).fetchall(), [('A', 2), ('B', 0)])
            self.assertEqual(db.execute(lab.CORRECT).fetchall(), [('A', 2), ('B', 0), ('C', 0)])

    def test_fixture_constraints_are_real(self):
        with contextlib.closing(lab.make_db()) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO products VALUES ('A','Дубль')")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO sales VALUES (99,'missing','paid',NULL)")

    def test_empty_comment_is_not_null(self):
        with contextlib.closing(lab.make_db("UPDATE sales SET comment = '' WHERE sale_id = 1;")) as db:
            self.assertEqual(db.execute(lab.WRONG["count_nullable_comment"]).fetchall(), [('A', 2), ('B', 0), ('C', 0)])

    def test_printed_output_matches_documented_cases(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            lab.main()
        expected = "".join(f"{name} {rows}\n" for name, _, rows in lab.CASES)
        self.assertEqual(output.getvalue(), expected)
        guide = Path(__file__).with_name("COUNT-LEFT-JOIN.md").read_text(encoding="utf-8")
        self.assertIn(expected.rstrip(), guide)

    def test_documented_sql_is_executable_and_matches_base(self):
        guide = Path(__file__).with_name("COUNT-LEFT-JOIN.md").read_text(encoding="utf-8")
        blocks = [part.split("```", 1)[0].strip() for part in guide.split("```sql\n")[1:]]
        self.assertEqual(len(blocks), 2)
        with contextlib.closing(lab.make_db()) as db:
            self.assertEqual(db.execute(blocks[0]).fetchall(), [('A', 2), ('B', 1), ('C', 1)])
            self.assertEqual(db.execute(blocks[1]).fetchall(), expected_by_sku(db))


if __name__ == "__main__":
    unittest.main()
