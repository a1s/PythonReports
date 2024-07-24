#! /usr/bin/env python
"""Fetch data from Sakila database for use in tests.

Sakila is an example database published by MySQL AB.
http://dev.mysql.com/doc/sakila/en/sakila.html

This module prepares a data sequence for direct load
in report builder tests to avoid a need for MySQL server.
The data is loaded from MySQL server running on localhost
without root password.

"""
# JFYI: size of the data file is about 3M.

import pickle

DATA_FILE = "sakila.dat"

# payments are tricky: they have both item fields (mapping-like)
# and attribute fields (structure-like)
class Payment(dict):
    customer = film = None

def load_dict(connection, key, sql):
    """Load a reference table from SQL"""
    rv = {}
    cursor = connection.cursor()
    cursor.execute(sql)
    columns = [item[0] for item in cursor.description]
    for row in cursor.fetchall():
        data = dict(zip(columns, row))
        rv[data[key]] = data
    return rv

def build():
    """Build data file"""
    import MySQLdb
    connection = MySQLdb.connect(user="root", db="sakila")

    # load reference data: customers and films
    customers = load_dict(connection, "customer_id", """
        SELECT * FROM customer
        WHERE customer_id IN (SELECT customer_id FROM payment)
    """)
    films = load_dict(connection, "film_id", """
        SELECT * FROM film
        WHERE film_id IN (SELECT i.film_id FROM inventory i
            INNER JOIN rental r ON i.inventory_id = r.inventory_id
            INNER JOIN payment p ON r.rental_id = p.rental_id
        )
    """)

    # load payment data, grouped by customers, ordered by film title
    cursor = connection.cursor()
    cursor.execute("""
        SELECT p.*, r.rental_date, r.return_date, i.film_id
        FROM payment p INNER JOIN rental r ON r.rental_id = p.rental_id
            INNER JOIN inventory i ON i.inventory_id = r.inventory_id
            INNER JOIN film f ON f.film_id = i.film_id
            INNER JOIN customer c ON c.customer_id = p.customer_id
        ORDER BY c.first_name, c.last_name, f.title
    """)
    columns = [item[0] for item in cursor.description]
    payments = []
    for row in cursor.fetchall():
        payment = Payment(zip(columns, row))
        payment.customer = customers[payment["customer_id"]]
        payment.film = films[payment["film_id"]]
        payments.append(payment)

    # write pickled data
    dat_file = open(DATA_FILE, "wb")
    pickle.dump(payments, dat_file, pickle.HIGHEST_PROTOCOL)
    dat_file.close()

# loader - used in tests
def load():
    with open(DATA_FILE, "rb") as data_file:
        payments = pickle.load(data_file, encoding="latin1")
    return payments

if __name__ == "__main__":
    # let this script be a module
    # (needed for unpickling)
    import sakila
    sakila.build()

# vim: set et sts=4 sw=4 :
