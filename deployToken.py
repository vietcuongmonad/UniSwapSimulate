
from algosdk.future import transaction
from algosdk.v2client import algod, indexer
from algosdk import account, mnemonic

TOKEN1_UNIT_NAME = "TOKEN_1"
TOKEN1_ASSET_NAME = "AlgoSwap Token1 Test"
TOKEN1_AMOUNT = 2 ** 32 - 1
TOKEN1_DECIMALS = 6
TOKEN2_UNIT_NAME = "TOKEN_2"
TOKEN2_ASSET_NAME = "AlgoSwap Token2 Test"
TOKEN2_AMOUNT = 2 ** 32 - 1
TOKEN2_DECIMALS = 6
LIQUIDITY_TOKEN_UNIT_NAME = "T_1/T_2"
LIQUIDITY_TOKEN_ASSET_NAME = "AlgoSwap Token_1/Token_2"
LIQUIDITY_TOKEN_AMOUNT = 2 ** 32 - 1
LIQUIDITY_TOKEN_DECIMALS = 6

DEVELOPER_MNEMONIC = "vanish frequent believe impact noble replace release strong couple cloud describe bike target spray impact mango media action slot knife window air vehicle above surge"
DEVELOPER_PRIVATE_KEY = mnemonic.to_private_key(DEVELOPER_MNEMONIC)
DEVELOPER_ADDRESS = account.address_from_private_key(DEVELOPER_PRIVATE_KEY)

ALGOD_TOKEN = "MWQJLR5Lc91ghWe8hzb7E1vr2Q24Gy5L1XsVDda6"
ALGOD_ADDRESS = "https://testnet-algorand.api.purestake.io/ps2"
INDEXER_TOKEN = ALGOD_TOKEN
INDEXER_ADDRESS = "https://testnet-algorand.api.purestake.io/idx2"

algod_client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS, headers = {"x-api-key": ALGOD_TOKEN})
indexer_client = indexer.IndexerClient(INDEXER_TOKEN, INDEXER_ADDRESS, headers = {"x-api-key": INDEXER_TOKEN})

def wait_for_confirmation(transaction_id):
    suggested_params = algod_client.suggested_params()
    algod_client.status_after_block(suggested_params.first + 4)
    result = indexer_client.search_transactions(txid=transaction_id)
    assert len(result['transactions']) == 1, result
    return result['transactions'][0]

def deploy_token1_token2():
    print(f"***Deploying {TOKEN1_UNIT_NAME} and {TOKEN2_UNIT_NAME}***")

    txn_1 = transaction.AssetConfigTxn(
        sender=DEVELOPER_ADDRESS,
        sp=algod_client.suggested_params(),
        total=TOKEN1_AMOUNT,
        default_frozen=False,
        unit_name = TOKEN1_UNIT_NAME,
        asset_name = TOKEN1_ASSET_NAME,
        manager=DEVELOPER_ADDRESS,
        reserve=DEVELOPER_ADDRESS,
        freeze=DEVELOPER_ADDRESS,
        clawback=DEVELOPER_ADDRESS,
        decimals=TOKEN1_DECIMALS
    ).sign(DEVELOPER_PRIVATE_KEY)

    txn_2 = transaction.AssetConfigTxn(
        sender=DEVELOPER_ADDRESS,
        sp=algod_client.suggested_params(),
        total=TOKEN2_AMOUNT,
        default_frozen=False,
        unit_name = TOKEN2_UNIT_NAME,
        asset_name = TOKEN2_ASSET_NAME,
        manager = DEVELOPER_ADDRESS,
        reserve = DEVELOPER_ADDRESS,
        freeze = DEVELOPER_ADDRESS,
        clawback = DEVELOPER_ADDRESS,
        decimals=TOKEN2_DECIMALS
    ).sign(DEVELOPER_PRIVATE_KEY)

    tx_id_1 = algod_client.send_transaction(txn_1)
    tx_id_2 = algod_client.send_transaction(txn_2)

    token1_asset_id = wait_for_confirmation(tx_id_1)['created-asset-index']
    token2_asset_id = wait_for_confirmation(tx_id_2)['created-asset-index']

    print(f"Deployed {TOKEN1_UNIT_NAME} with asset ID {token1_asset_id} \
        | Tx ID: https://testnet.algoexplorer.io/tx/{tx_id_1}")
    print(f"Deployed {TOKEN2_UNIT_NAME} with asset ID {token2_asset_id} \
        | Tx ID: https://testnet.algoexplorer.io/tx/{tx_id_2}")
    
    print()
    return token1_asset_id, token2_asset_id

def deploy_liquidity_token():
    print(f"Deploying token {LIQUIDITY_TOKEN_UNIT_NAME}")

    txn = transaction.AssetConfigTxn(
        sender=DEVELOPER_ADDRESS,
        sp=algod_client.suggested_params(),
        total=LIQUIDITY_TOKEN_AMOUNT,
        default_frozen=False,
        unit_name=LIQUIDITY_TOKEN_UNIT_NAME,
        asset_name=LIQUIDITY_TOKEN_ASSET_NAME,
        manager=DEVELOPER_ADDRESS,
        reserve=DEVELOPER_ADDRESS,
        freeze=DEVELOPER_ADDRESS,
        clawback=DEVELOPER_ADDRESS,
        decimals=LIQUIDITY_TOKEN_DECIMALS
    ).sign(DEVELOPER_PRIVATE_KEY)

    tx_id = algod_client.send_transaction(txn)

    liquidity_token_asset_id = int(
        wait_for_confirmation(tx_id)['created-asset-index']
    )

    print(f"Deployed {LIQUIDITY_TOKEN_UNIT_NAME} with asset ID {liquidity_token_asset_id} \
        | Tx ID: https://testnet.algoexplorer.io/tx/{tx_id}")
    print()
    return liquidity_token_asset_id

token1_asset_id = 55660342
token2_asset_id = 55660344
liquidity_token_asset_id = 55666101

