
from .ABI.eMTVABI import eMTVABI

from web3 import Web3

import time


class eMTV:

    def __init__(self, host, account, contract_address=None, chain_id=3):

        self.__w3 = Web3(Web3.HTTPProvider(host))
        self.__account = account
        self.__chain_id = chain_id

        if chain_id == 3:
            self.contract = self.__w3.eth.contract(Web3.toChecksumAddress("0x69234671c41180535759Bb04F4e07A4F2610e834"), abi=eMTVABI)
        else:
            self.contract = self.__w3.eth.contract(Web3.toChecksumAddress(contract_address), abi=eMTVABI)

    def allowance(self, spender):
        spender = Web3.toChecksumAddress(spender)
        address = Web3.toChecksumAddress(self.__account.address)
        return self.contract.functions.allowance(address, spender).call()

    def approve(self, spender, amount):

        nonce = self.__w3.eth.getTransactionCount(self.__account.address)
        gas = self.contract.functions.approve(spender, amount).estimateGas(
            {'from': self.__account.address})

        transaction = self.contract.functions.approve(spender, amount).buildTransaction({
            'from': self.__account.address,
            'chainId': self.__chain_id,
            'gas': gas,
            'nonce': nonce,
        })

        signed_txn = self.__w3.eth.account.signTransaction(transaction, private_key=self.__account.privateKey)
        try:
            a = self.__w3.eth.sendRawTransaction(signed_txn.rawTransaction)
        except ValueError as e:
            raise e

        while True:
            time.sleep(1)
            status = self.__w3.eth.getTransaction(a)
            print(status)
            if status['blockHash'] is not None:
                break

        return self.allowance(spender)

    def balance_of(self, address):
        return self.contract.functions.balanceOf(address).call()

    def decimals(self):
        return self.contract.functions.decimals().call()

    def decrease_allowance(self, spender, amount):
        return self.contract.functions.decreaseAllowance().call()

    def increase_allowance(self, spender, amount):
        return self.contract.functions.increaseAllowance().call()