import pprint
import datetime
import json
from ethtx import EthTx, EthTxConfig
from ethtx.models.decoded_model import DecodedTransaction
from ethtx.models.w3_model import W3Transaction, W3Receipt, W3CallTree

ethtx_config = EthTxConfig(
    mongo_connection_string="mongomock://localhost/db",  ##MongoDB connection string,
    etherscan_api_key = "UWB1WRG4RT9N3TRKDBZ8JW96WG7KQZAT2V",  ##Etherscan API key,
    web3nodes = {
                "mainnet": {
                    "hook": "http://18.208.139.31:8545", # multiple nodes supported, separate them with comma
                    "poa": False  # represented by bool value
                }
            },
    default_chain = "mainnet",
    etherscan_urls = {"mainnet": "https://api.etherscan.io/api",},
)

ethtx = EthTx.initialize(ethtx_config)
web3provider = ethtx.providers.web3provider

w3transaction: W3Transaction = web3provider.get_transaction(
    '0x5f24e3da0a343e89f2430f7877838568acd537fd3b76edda1048c2c11dcd9e0b')

class Block:

    def __init__(self):
        self.timestamp = datetime.datetime.now()

w3receipt: W3Receipt = web3provider.get_receipt(w3transaction.hash.hex())
w3calls: W3CallTree = web3provider.get_calls(w3transaction.hash.hex())

rootCall = w3calls.to_object()

txMetadata = w3transaction.to_object(w3receipt)
block = Block()

events = [log.to_object() for log in w3receipt.logs]

proxies = ethtx.decoders.get_proxies(rootCall, 'mainnet')
abi_decoded_events = ethtx.decoders.abi_decoder.decode_events(events, block, txMetadata, proxies=proxies, chain_id='mainnet')
abi_decoded_calls = ethtx.decoders.abi_decoder.decode_calls(rootCall, block, txMetadata, proxies, 'mainnet')
abi_decoded_transfers = ethtx.decoders.abi_decoder.decode_transfers(abi_decoded_calls, abi_decoded_events, proxies, 'mainnet')
abi_decoded_balances = ethtx.decoders.abi_decoder.decode_balances(abi_decoded_transfers)

pprint.pprint(abi_decoded_balances)