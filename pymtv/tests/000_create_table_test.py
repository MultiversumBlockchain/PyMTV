import unittest
import pymtv

unittest.TestLoader.sortTestMethodsUsing = None


class TestCreateTable(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestCreateTable, self).__init__(*args, **kwargs)
        self.host = "https://ropsten.infura.io/v3/xxxxxxxxxx"
        self.databaseAddress = ""
        self.privateKey = ""

    def test_0000_config(self):
        self.assertNotEqual(self.host, "", msg='Please set the self.host value')
        self.assertNotEqual(self.databaseAddress, "", msg='Please set the self.databaseAddress value')
        self.assertNotEqual(self.privateKey, "", msg='Please set the self.privateKey value')

    def test_0010_connection(self):
        self.conn = pymtv.connect(host=self.host, db_address=self.databaseAddress, private_key=self.privateKey)
        self.assertTrue(self.conn.is_connected())

    '''
    def test_0020_create_table(self):
        
        conn = pymtv.connect(host=self.host, db_address=self.databaseAddress, private_key=self.privateKey)
        self.assertTrue(conn.is_connected())

        statement = "CREATE TABLE people (first_name text, last_name text, city text)"

        cursor = conn.cursor()

        cursor.execute(statement)
    '''

    def test_0030_show_tables(self):
        conn = pymtv.connect(host=self.host, db_address=self.databaseAddress, private_key=self.privateKey)
        self.assertTrue(conn.is_connected())

        cursor = conn.cursor()

        cursor.execute("SHOW TABLES")

        rows = cursor.fetchall()

        self.assertIsNotNone(rows)

    def test_0040_insert(self):

        david = {
            "first_name": "David",
            "last_name": "Wilson",
            "birth_place": "Madrid",
            "birth_date": "4/16/1976",
        }

        conn = pymtv.connect(host=self.host, db_address=self.databaseAddress, private_key=self.privateKey)
        self.assertTrue(conn.is_connected())

        cursor = conn.cursor()
        cursor.execute("INSERT INTO people ( first_name, last_name, birth_place, birth_date ) VALUES ('{}', '{}', '{}', '{}')".format(david['first_name'], david['last_name'], david['birth_place'], david['birth_date']))

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM people WHERE first_name = '{}' AND last_name = '{}' AND  birth_place = '{}' AND birth_date = '{}'".format(david['first_name'], david['last_name'], david['birth_place'], david['birth_date']))

        row = cursor.fetchone()

        self.assertIsNotNone(row)

        self.assertEqual(row[0], david['first_name'])
        self.assertEqual(row[1], david['last_name'])
        self.assertEqual(row[2], david['birth_date'])
        self.assertEqual(row[3], david['birth_place'])

    def test_0050_select_fetch_one(self):
        conn = pymtv.connect(host=self.host, db_address=self.databaseAddress, private_key=self.privateKey)
        self.assertTrue(conn.is_connected())

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM people")

        row = cursor.fetchone()

        self.assertIsNotNone(row)

    def test_0060_update(self):
        p1 = {
            "first_name": "Claire",
            "last_name": "Darcy",
            "birth_place": "Atlanta",
            "birth_date": "8/26/4030",
        }

        p2 = {
            "first_name": "Angel",
            "last_name": "Thomson",
            "birth_place": "Prague",
            "birth_date": "5/19/1990",
        }

        conn = pymtv.connect(host=self.host, db_address=self.databaseAddress, private_key=self.privateKey)
        self.assertTrue(conn.is_connected())

        cursor = conn.cursor()
        cursor.execute("INSERT INTO people ( first_name, last_name, birth_place, birth_date ) VALUES ('{}', '{}', '{}', '{}')"
                       .format(p1['first_name'], p1['last_name'], p1['birth_place'], p1['birth_date']))

        cursor.execute("UPDATE people SET first_name = '{}', last_name = '{}', birth_place = '{}', birth_date = '{}' WHERE first_name = '{}' AND last_name = '{}' AND birth_date = '{}' AND birth_place = '{}".
                       format(p2['first_name'], p2['last_name'], p2['birth_place'], p2['birth_date'], p1['first_name'], p1['last_name'], p1['birth_place'], p1['birth_date']))

        cursor.execute("SELECT * FROM people WHERE first_name = '{}' AND last_name = '{}' AND birth_date = '{}' AND birth_place = '{}".
                       format(p2['first_name'], p2['last_name'], p2['birth_place'], p2['birth_date']))

        row = cursor.fetchone()

    def test_0100_delete(self):
        conn = pymtv.connect(host=self.host, db_address=self.databaseAddress, private_key=self.privateKey)
        self.assertTrue(conn.is_connected())

        cursor = conn.cursor()

        cursor.execute("DELETE FROM people")

    '''
    def test_1000_drop_table(self):
        pass
        conn = pymtv.connect(host=self.host, db_address=self.databaseAddress, private_key=self.privateKey)
        self.assertTrue(conn.is_connected())

        cursor = conn.cursor()

        cursor.execute("DROP TABLE people")
    '''


if __name__ == '__main__':
    unittest.main()