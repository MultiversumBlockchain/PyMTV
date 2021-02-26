from web3 import Web3

import time

from .SQLParser import Parser
from .cursors import Cursor
from .error import *

import traceback

from .ABI.DatabaseABI import DatabaseABI

from .eMTV import eMTV
from .factory import Factory

comparator = {
    '=': '==',
    '!=': '!=',
    '<>': '!='
}


class Connection:

    def __init__(self, host='localhost', db_address=None, private_key=None, chain_id=3):
        self.__host = host
        self.__db_address = db_address
        self.__private_key = private_key
        self.__w3 = None
        self.__chain_id = chain_id
        self.__cursorclass = Cursor
        self.__db_contract = None
        self._result = None
        self.__account = None
        self.__emtv = None

        self.__factory = Factory(host, chain_id=chain_id)
        self.__tables = dict()

        self.connect()

    def __enter__(self):
        return self

    def close(self):
        pass

    @property
    def open(self):
        return self.__w3 is not None

    def ping(self, reconnect=True):
        if self.__w3 is None:
            if reconnect:
                self.connect()
                reconnect = False
            else:
                raise err.Error("Already closed")
        try:
            self.__w3.isConnected()

        except Exception:
            if reconnect:
                self.connect()
                self.ping(False)
            else:
                raise

    def is_connected(self):
        return self.__w3.isConnected()

    def __get_nonce(self):
        return self.__w3.eth.get_transaction_count(self.__account.address)

    def __sign_transaction(self, transaction):
        return self.__w3.eth.account.sign_transaction(transaction, private_key=self.__private_key)

    def __load_db_info(self):
        raw_tables_data = self.__db_contract.functions.showTables().call()

        for i in range(0, len(raw_tables_data), 2):
            table_name = Web3.toText(raw_tables_data[i + 1]).rstrip('\x00')
            if table_name != '':

                self.__tables[table_name] = {
                    'index': Web3.toInt(raw_tables_data[i]),
                    'fields': dict()
                }

                raw_desc_table_data = self.__db_contract.functions.desc(self.__tables[table_name]['index']).call()
                for j in range(0, len(raw_desc_table_data), 2):
                    field_name = Web3.toText(raw_desc_table_data[j + 1]).rstrip('\x00')

                    self.__tables[table_name]['fields'][field_name] = {
                        'index': Web3.toInt(raw_desc_table_data[j])
                    }

    def connect(self, dsn=None):
        self.__w3 = Web3(Web3.HTTPProvider(self.__host))

        self.__db_contract = self.__w3.eth.contract(Web3.toChecksumAddress(self.__db_address), abi=DatabaseABI)
        self.__account = self.__w3.eth.account.privateKeyToAccount(self.__private_key)
        self.__emtv = eMTV(self.__host, self.__account)

        self.__load_db_info()

    def cursor(self, cursor=None):
        if cursor:
            return cursor(self)
        return self.__cursorclass(self)

    def __build_transaction(self, transaction):
        nonce = self.__w3.eth.get_transaction_count(self.__account.address)
        gas = transaction.estimateGas({
            'from': self.__account.address
        })

        tnx = transaction.buildTransaction({
            'from': self.__account.address,
            'chainId': self.__chain_id,
            'gas': gas,
            'nonce': nonce
        })

        return self.__w3.eth.account.sign_transaction(tnx, private_key=self.__private_key)

    def query(self, sql, unbuffered=False):
        parser = Parser()

        parsed = parser.parse(sql)
        statement = parsed['function'].upper()

        if statement == 'CREATE':
            if not self.__w3.isConnected():
                raise Error('The connection to the database has been closed.')

            table = parsed['table']

            if table in self.__tables:
                raise SQLError("Table '{}' exists.".format(table))

            columns = []
            for i in range(0, len(parsed['columns'])):
                columns.append(str(i).encode())
                columns.append(parsed['columns'][i]['name'].encode())

            create_table_price = self.__factory.get_create_table_price()
            allowance = self.__emtv.allowance(self.__db_address)

            if allowance < create_table_price:
                self.__emtv.approve(self.__db_address, create_table_price)

            trans = self.__db_contract.functions.createTable(table.encode(), columns)

            signed_txn = self.__build_transaction(trans)
            a = self.__w3.eth.send_raw_transaction(signed_txn.rawTransaction)

            while True:
                time.sleep(1)
                status = self.__w3.eth.get_transaction(a)
                if status['blockHash'] is not None:
                    break

        elif statement == 'DROP':
            tables = parsed['tables']

            if not self.__w3.isConnected():
                raise Error('The connection to the database has been closed.')

            for table in tables:

                if table not in self.__tables:
                    raise SQLError("Table '{}' not found.".format(table))

                drop_table_price = self.__factory.get_drop_table_price()
                allowance = self.__emtv.allowance(self.__db_address)

                if allowance < drop_table_price:
                    self.__emtv.approve(self.__db_address, drop_table_price)

                signed_txn = self.__build_transaction(self.__db_contract.functions.dropTable(self.__tables[table]['index']))
                self.__send_raw_transaction(signed_txn.rawTransaction)

                self.__load_db_info()

        elif statement == 'SHOW':

            rows = []

            if parsed['item'] == 'tables':
                self.__load_db_info()

            for table in self.__tables:
                rows.append([self.__tables[table]['index'], [table]])

            self._result = MTVResult(self, rows=rows, description=['index', 'name'])

        elif statement == 'SELECT':

            tables = parsed['tables']
            columns = parsed['columns']

            results = list()
            data = dict()

            if not self.__w3.isConnected():
                raise Error('The connection to the database has been closed.')

            if type(tables) == type(''):
                tables = [tables]

            for table in tables:
                if table not in self.__tables:
                    raise SQLError("Table '{}' not found.".format(table))

                data[table] = self.__db_contract.functions.selectAll(self.__tables[table]['index'], 0, 50).call()
                #data[table] = self.__db_contract.functions.selectAll(self.__tables[table]['index'], 0, 50).call(block_identifier=10000)

                for row in data[table]:
                    to_be_select = False

                    expression = ""
                    if len(row) > 0:
                        if 'where' in parsed:
                            where = parsed['where']

                            for clausole in where:
                                if isinstance(clausole, str):
                                    expression += " {} ".format(clausole.lower())
                                else:
                                    if clausole[0] not in self.__tables[table]['fields']:
                                        raise SQLError("Column '{}' not found.".format(clausole[0]))

                                    if self.__tables[table]['fields'][clausole[0]]['index'] < len(row):
                                        value = row[self.__tables[table]['fields'][clausole[0]]['index']]
                                        expression += (Web3.toHex(value.replace('\'', '').encode()) + " " + comparator['='] + " " + Web3.toHex(
                                            clausole[2].replace('\'', '').encode()))

                            to_be_select = eval(expression)

                    if to_be_select or 'where' not in parsed:
                        if '*' in columns:
                            for k in range(len(row), len(self.__tables[table]['fields'])):
                                row.append("")
                            results.append(row)
                        else:
                            r = list()
                            for column in columns:
                                r.append(row[self.__tables[table]['fields'][column]['index']])
                            results.append(r)

            if '*' in columns:
                self._result = MTVResult(self, rows=results, description=self.__tables[table]['fields'])
            else:
                self._result = MTVResult(self, rows=results, description=columns)

        elif statement == 'UPDATE':

            table = parsed['table']
            columns = parsed['columns']
            values = parsed['sqlValues']

            if not self.__w3.isConnected():
                raise Error('The connection to the database has been closed.')

            if table not in self.__tables:
                raise SQLError("Table '{}' not found.".format(table))

            data = self.__db_contract.functions.selectAll(self.__tables[table]['index'], 0, 50).call()

            for i in range(0, len(data)):
                row = data[i]
                expression = ""
                to_be_update = False
                try:
                    if len(row) > 0:
                        if 'where' in parsed:
                            where = parsed['where']

                            for clausole in where:
                                if isinstance(clausole, str):
                                    expression += " {} ".format(clausole.lower())
                                else:

                                    if clausole[0] not in self.__tables[table]['fields']:
                                        raise SQLError("Column '{}' not found.".format(clausole[0]))
                                    
                                    if self.__tables[table]['fields'][clausole[0]]['index'] < len(row):
                                        value = row[self.__tables[table]['fields'][clausole[0]]['index']]
                                        expression += (Web3.toHex(value.replace('\'', '').encode()) + " " + comparator['='] + " " + Web3.toHex(clausole[2].encode()))

                            to_be_update = eval(expression)

                    if to_be_update or 'where' not in parsed:

                        for j in range(0, len(columns)):
                            column = columns[j]
                            index = self.__tables[table]['fields'][column]['index']
                            row[index] = values[j]

                        update_price = self.__factory.get_update_price()
                        allowance = self.__emtv.allowance(self.__db_address)

                        if allowance < update_price:
                            self.__emtv.approve(self.__db_address, update_price)

                        signed_txn = self.__build_transaction(self.__db_contract.functions.deleteDirect(Web3.toInt(self.__tables[table]['index']), Web3.toInt(i)))
                        self.__send_raw_transaction(signed_txn.rawTransaction)

                except Exception as e:
                    raise e

        elif statement == 'INSERT':
            table = parsed['table']
            columns = parsed['columns']
            values = parsed['sqlValues']

            row = list()

            if not self.__w3.isConnected():
                raise Error('The connection to the database has been closed.')

            if table not in self.__tables:
                raise SQLError("Table '{}' not found.".format(table))

            for field in self.__tables[table]['fields']:
                value = ""

                if field in columns:
                    index = columns.index(field)
                    value = values[index].replace('\'', '')

                row.append(value)

            insert_price = self.__factory.get_insert_price()
            allowance = self.__emtv.allowance(self.__db_address)

            if allowance < insert_price:
                self.__emtv.approve(self.__db_address, insert_price)

            signed_txn = self.__build_transaction(self.__db_contract.functions.insert(Web3.toInt(self.__tables[table]['index']), row))
            self.__send_raw_transaction(signed_txn.rawTransaction)

            self._result = MTVResult(self, affected_rows=1)

        elif statement == 'DELETE':

            table = parsed['table']

            results = list()

            if not self.__w3.isConnected():
                raise Error('The connection to the database has been closed.')

            if table not in self.__tables:
                raise SQLError("Table '{}' not found.".format(table))

            data = self.__db_contract.functions.selectAll(self.__tables[table]['index'], 0, 50).call()

            affected_rows = 0

            for i in range(0, len(data)):
                row = data[i]
                to_be_delete = False
                try:

                    expression = ""
                    if len(row) > 0:
                        if 'where' in parsed:
                            where = parsed['where']

                            for clausole in where:
                                if isinstance(clausole, str):
                                    expression += " {} ".format(clausole.lower())
                                else:
                                    if self.__tables[table]['fields'][clausole[0]]['index'] < len(row):
                                        value = row[self.__tables[table]['fields'][clausole[0]]['index']]
                                        expression += (Web3.toHex(value.replace('\'', '').encode()) + " " + comparator['='] + " " + Web3.toHex(clausole[2].encode()))

                                    else:
                                        raise Exception

                            to_be_delete = eval(expression)

                    if to_be_delete or 'where' not in parsed:
                        affected_rows += 1

                        delete_price = self.__factory.get_delete_price()
                        allowance = self.__emtv.allowance(self.__db_address)

                        if allowance < delete_price:
                            self.__emtv.approve(self.__db_address, delete_price)

                        signed_txn = self.__build_transaction(self.__db_contract.functions.deleteDirect(Web3.toInt(self.__tables[table]['index']), Web3.toInt(i)))
                        self.__send_raw_transaction(signed_txn.rawTransaction)

                except Exception as e:
                    raise e

            self._result = MTVResult(self, affected_rows=affected_rows)

    def __send_raw_transaction(self, raw_transaction):
        a = self.__w3.eth.send_raw_transaction(raw_transaction)

        while True:
            time.sleep(1)
            status = self.__w3.eth.get_transaction(a)
            if status['blockHash'] is not None:
                return True


class MTVResult:
    def __init__(self, connection, rows=None, description=None, affected_rows=None):
        """
        :type connection: Connection
        """
        self.connection = connection
        self.affected_rows = affected_rows
        self.insert_id = None
        self.server_status = None
        self.warning_count = 0
        self.message = None
        self.field_count = 0
        self.description = description
        self.rows = rows
        self.has_next = None
        self.affected_rows = len(self.rows) if self.rows is not None else None

    def __del__(self):
        pass

