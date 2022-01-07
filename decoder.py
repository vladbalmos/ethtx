import sys
from inspect import trace
from eth_typing.evm import BlockNumber
from hexbytes import HexBytes
from ethtx.models._types import THexBytes
from attributedict.collections import AttributeDict
import fileinput
import pprint
import datetime
import json
from ethtx import EthTx, EthTxConfig
from ethtx.models.decoded_model import DecodedTransaction
from ethtx.models.w3_model import W3Log, W3Transaction, W3Receipt, W3CallTree

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

decoderInput = ''
for line in fileinput.input():
    decoderInput += line
    
decoderInput = json.loads(decoderInput)

if not 'result' in decoderInput['trace']:
    sys.exit(0)

block = None

if decoderInput['tx']['decBlockNumber']:
    block = web3provider.get_block(decoderInput['tx']['blockHash'])
else:
    block = web3provider.get_block('latest')


txTrace = AttributeDict(decoderInput['trace']['result'])
jsTx = AttributeDict(decoderInput['tx'])
tx = W3Transaction(
    chain_id='mainnet',
    blockHash=jsTx.blockHash or block.hash,
    blockNumber=jsTx.decBlockNumber or block.number,
    from_address=jsTx['from'],
    gas=jsTx.decGas,
    gasPrice=jsTx.decGasPrice,
    hash=HexBytes(jsTx.hash),
    input=jsTx.input,
    nonce=jsTx.decNonce,
    r=jsTx.r,
    s=jsTx.s,
    to=jsTx.to,
    transactionIndex=jsTx.decTransactionIndex or 0,
    v=int(jsTx.v, 16),
    value=jsTx.decValue
)

txStatus = 1
logs = []

if 'error' in decoderInput['trace']['result']:
    txStatus = 0
else:
    logs = [
        W3Log(
            tx_hash=tx.hash.hex(),
            chain_id='mainnet',
            address=_log['address'],
            blockHash=tx.blockHash,
            blockNumber=tx.blockNumber,
            data=_log['data'],
            logIndex=int(_log['logIndex'], 16),
            removed=_log['removed'],
            topics=[
                HexBytes(_t)
                for _t in _log['topics']
            ],
            transactionHash=tx.hash.hex(),
            transactionIndex=tx.transactionIndex
        )
        for _log in txTrace.logs
    ]
    

w3receipt = W3Receipt(
    tx_hash=tx.hash.hex(),
    chain_id='mainnet',
    blockHash=tx.blockHash,
    blockNumber=tx.blockNumber,
    cumulativeGasUsed=int(txTrace.gasUsed, 16),
    from_address=tx.from_address,
    gasUsed=int(txTrace.gasUsed, 16),
    transactionIndex=tx.transactionIndex,
    transactionHash=tx.hash.hex(),
    logsBloom=0x0,
    status=txStatus,
    logs=logs
)

class Block:

    def __init__(self):
        self.timestamp = datetime.datetime.now()
    
w3calls: W3CallTree = web3provider.get_calls(tx.hash.hex(), chain_id='mainnet', trace=txTrace)

rootCall = w3calls.to_object()

txMetadata = tx.to_object(w3receipt)

events = [log.to_object() for log in w3receipt.logs]

proxies = ethtx.decoders.get_proxies(rootCall, 'mainnet')
abi_decoded_events = ethtx.decoders.abi_decoder.decode_events(events, block.to_object(), txMetadata, proxies=proxies, chain_id='mainnet')
abi_decoded_calls = ethtx.decoders.abi_decoder.decode_calls(rootCall, block.to_object(), txMetadata, proxies, 'mainnet')
abi_decoded_transfers = ethtx.decoders.abi_decoder.decode_transfers(abi_decoded_calls, abi_decoded_events, proxies, 'mainnet')
abi_decoded_balances = ethtx.decoders.abi_decoder.decode_balances(abi_decoded_transfers)

print(json.dumps({
    'events': [ e.dict() for e in abi_decoded_events ],
    'calls': abi_decoded_calls.dict(),
    'transfers': [ t.dict() for t in abi_decoded_transfers ],
    'balances': [ b.dict() for b in abi_decoded_balances ]
}, default=str))
