"""One SQL aggregation lab. Standard library only; synthetic in-memory data."""

import sqlite3


SCHEMA = """
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    status TEXT NOT NULL,
    total_rub INTEGER NOT NULL CHECK (total_rub >= 0)
);
CREATE TABLE items (
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    line_no INTEGER NOT NULL,
    PRIMARY KEY (order_id, line_no)
);
INSERT INTO orders VALUES
    (1, 'paid', 1000), (2, 'paid', 600), (3, 'cancelled', 900);
INSERT INTO items VALUES (1, 1), (1, 2), (2, 1), (3, 1);
"""

QUERIES = {
    "JOIN": """
        SELECT SUM(o.total_rub)
        FROM orders AS o
        JOIN items AS i ON i.order_id = o.order_id
        WHERE o.status = 'paid';
    """,
    "DISTINCT": """
        SELECT SUM(DISTINCT o.total_rub)
        FROM orders AS o
        JOIN items AS i ON i.order_id = o.order_id
        WHERE o.status = 'paid';
    """,
    "EXISTS": """
        SELECT COALESCE(SUM(o.total_rub), 0)
        FROM orders AS o
        WHERE o.status = 'paid'
          AND EXISTS (
            SELECT 1 FROM items AS i
            WHERE i.order_id = o.order_id
          );
    """,
}

CASES = (
    ("base", "", (2600, 1600, 1600)),
    ("same_price", """
        INSERT INTO orders VALUES (4, 'paid', 1000);
        INSERT INTO items VALUES (4, 1);
    """, (3600, 1600, 2600)),
    ("no_items", """
        INSERT INTO orders VALUES (4, 'paid', 2500);
    """, (2600, 1600, 1600)),
    ("more_lines", """
        INSERT INTO items VALUES (1, 3);
    """, (3600, 1600, 1600)),
    ("no_paid", """
        UPDATE orders SET status = 'cancelled';
    """, (None, None, 0)),
    ("empty", """
        DELETE FROM items;
        DELETE FROM orders;
    """, (None, None, 0)),
)


def make_db(changes=""):
    """Return a fresh example database. changes is local trusted exercise SQL."""
    db = sqlite3.connect(":memory:")
    try:
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript(SCHEMA)
        db.executescript(changes)
    except Exception:
        db.close()
        raise
    return db


def results(db):
    return tuple(
        db.execute(QUERIES[key]).fetchone()[0]
        for key in ("JOIN", "DISTINCT", "EXISTS")
    )


def main():
    for name, changes, expected in CASES:
        db = make_db(changes)
        try:
            actual = results(db)
            if actual != expected:
                raise AssertionError((name, expected, actual))
            print(name, actual)
        finally:
            db.close()


if __name__ == "__main__":
    main()
