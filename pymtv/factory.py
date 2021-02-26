
from .ABI.factoryABI import FactoryABI

from web3 import Web3


class Factory:

    def __init__(self, host, chain_id=3):

        self.w3 = Web3(Web3.HTTPProvider(host))
        if chain_id == 3:
            self.contract = self.w3.eth.contract(Web3.toChecksumAddress("0x761Dbb632f8789cCedA21Eb47844135Fc2484C57"), abi=FactoryABI)
        else:
            self.contract = self.w3.eth.contract(Web3.toChecksumAddress("TBD"), abi=FactoryABI)

    def get_update_price(self):
        return self.contract.functions.UpdatePrice().call()

    def get_insert_price(self):
        return self.contract.functions.InsertIntoPrice().call()

    def get_delete_price(self):
        return self.contract.functions.DeleteFromPrice().call()

    def get_drop_table_price(self):
        return self.contract.functions.DropTablePrice().call()

    def get_create_table_price(self):
        return self.contract.functions.CreateTablePrice().call()

    def get_create_database_price(self):
        return self.contract.functions.CreateDatabasePrice().call()