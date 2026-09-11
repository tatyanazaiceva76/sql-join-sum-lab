"""COUNT after LEFT JOIN: synthetic in-memory data, standard library only."""

import sqlite3


SCHEMA = """
CREATE TABLE products (
    sku TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL
);
CREATE TABLE sales (
    sale_id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL REFERENCES products(sku),
    status TEXT NOT NULL,
    comment TEXT
);
INSERT INTO products VALUES ('A','Блокнот'),('B','Папка'),('C','Альбом');
INSERT INTO sales VALUES
    (1,'A','paid',NULL),
    (2,'A','paid','Учебная запись'),
    (3,'C','cancelled',NULL);
"""

CORRECT = """
SELECT p.sku, COUNT(s.sale_id) AS paid_rows
FROM products AS p
LEFT JOIN sales AS s ON s.sku = p.sku AND s.status = 'paid'
GROUP BY p.sku
ORDER BY p.sku;
"""

WRONG = {
    "count_star": CORRECT.replace("COUNT(s.sale_id)", "COUNT(*)"),
    "count_nullable_comment": CORRECT.replace("COUNT(s.sale_id)", "COUNT(s.comment)"),
    "filter_in_where": """
        SELECT p.sku, COUNT(s.sale_id) AS paid_rows
        FROM products AS p
        LEFT JOIN sales AS s ON s.sku = p.sku
        WHERE s.status = 'paid'
        GROUP BY p.sku ORDER BY p.sku;
    """,
    "where_or_null": """
        SELECT p.sku, COUNT(s.sale_id) AS paid_rows
        FROM products AS p
        LEFT JOIN sales AS s ON s.sku = p.sku
        WHERE s.status = 'paid' OR s.sale_id IS NULL
        GROUP BY p.sku ORDER BY p.sku;
    """,
}

CASES = (
    ("base", "", [('A', 2), ('B', 0), ('C', 0)]),
    ("empty_sales", "DELETE FROM sales;", [('A', 0), ('B', 0), ('C', 0)]),
    ("no_paid", "UPDATE sales SET status = 'cancelled';", [('A', 0), ('B', 0), ('C', 0)]),
    ("new_paid", "INSERT INTO sales VALUES (4,'C','paid',NULL);", [('A', 2), ('B', 0), ('C', 1)]),
    ("unpaid_only", "INSERT INTO sales VALUES (4,'B','new',NULL);", [('A', 2), ('B', 0), ('C', 0)]),
    ("same_name", "UPDATE products SET name = 'Одинаковое название';", [('A', 2), ('B', 0), ('C', 0)]),
    ("empty_catalog", "DELETE FROM sales; DELETE FROM products;", []),
)


def make_db(changes=""):
    """changes is trusted local exercise SQL, not an external user input."""
    db = sqlite3.connect(":memory:")
    try:
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript(SCHEMA)
        db.executescript(changes)
    except Exception:
        db.close()
        raise
    return db


def main():
    for name, changes, expected in CASES:
        db = make_db(changes)
        try:
            actual = db.execute(CORRECT).fetchall()
            if actual != expected:
                raise AssertionError((name, expected, actual))
            print(name, actual)
        finally:
            db.close()


if __name__ == "__main__":
    main()
