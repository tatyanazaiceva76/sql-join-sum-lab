"""Independent checks for the small public lab; no network or external data."""

import contextlib
import io
import unittest

import sql_join_lab as lab


def expected_by_order_id(db):
    ids_with_items = {row[0] for row in db.execute("SELECT order_id FROM items")}
    return sum(
        total
        for order_id, status, total in db.execute(
            "SELECT order_id, status, total_rub FROM orders"
        )
        if status == "paid" and order_id in ids_with_items
    )


class SQLJoinLabTests(unittest.TestCase):
    def check_case(self, name):
        _, changes, expected = next(case for case in lab.CASES if case[0] == name)
        db = lab.make_db(changes)
        self.addCleanup(db.close)
        self.assertEqual(lab.results(db), expected)
        self.assertEqual(lab.results(db)[2], expected_by_order_id(db))
        self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_base(self):
        self.check_case("base")

    def test_same_price(self):
        self.check_case("same_price")

    def test_no_items(self):
        self.check_case("no_items")

    def test_more_lines(self):
        self.check_case("more_lines")

    def test_no_paid(self):
        self.check_case("no_paid")

    def test_empty(self):
        self.check_case("empty")

    def test_wrong_fixes_are_detected(self):
        wrong_queries = {
            "JOIN": lab.QUERIES["JOIN"],
            "DISTINCT": lab.QUERIES["DISTINCT"],
            "missing_item_condition": (
                "SELECT COALESCE(SUM(total_rub), 0) FROM orders WHERE status='paid'"
            ),
        }
        for label, query in wrong_queries.items():
            counterexamples = []
            for name, changes, _ in lab.CASES:
                db = lab.make_db(changes)
                try:
                    if db.execute(query).fetchone()[0] != expected_by_order_id(db):
                        counterexamples.append(name)
                finally:
                    db.close()
            with self.subTest(query=label):
                self.assertTrue(counterexamples, "Wrong fix escaped every scenario")

    def test_printed_output(self):
        expected = (
            "base (2600, 1600, 1600)\n"
            "same_price (3600, 1600, 2600)\n"
            "no_items (2600, 1600, 1600)\n"
            "more_lines (3600, 1600, 1600)\n"
            "no_paid (None, None, 0)\n"
            "empty (None, None, 0)\n"
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            lab.main()
        self.assertEqual(output.getvalue(), expected)


if __name__ == "__main__":
    unittest.main()
