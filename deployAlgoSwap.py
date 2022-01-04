import algoSwapCurrent
from pyteal import *
from algosdk.v2client import algod, indexer

ALGOD_TOKEN = "MWQJLR5Lc91ghWe8hzb7E1vr2Q24Gy5L1XsVDda6"
ALGOD_ADDRESS = "https://testnet-algorand.api.purestake.io/ps2"
INDEXER_TOKEN = ALGOD_TOKEN
INDEXER_ADDRESS = "https://testnet-algorand.api.purestake.io/idx2"

algod_client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS, headers = {"x-api-key": ALGOD_TOKEN})
indexer_client = indexer.IndexerClient(INDEXER_TOKEN, INDEXER_ADDRESS, headers = {"x-api-key": INDEXER_TOKEN})

def compile_manager():
    print("Compiling exchange manager application...")

    manager_approve_in_teal = compileTeal(algoSwapCurrent.approval_program(), Mode.Application)
    compile_response = algod_client.compile(manager_approve_in_teal) # <-- Error: here
    #manager_approve_code = base64.b64decode(compile_response['result'])
    #MANAGER_APPROVE_BYTECODE_LEN = len(manager_approve_code)
    #MANAGER_APPROVE_ADDRESS = compile_response['hash']

    #print(compile_response)

    #manager_clear_in_teal = compileTeal(algoSwapCurrent.clear_program(), Mode.Application)
    #compile_response = algod_client.compile(manager_clear_in_teal)


def deploy_exchange_manager(manager_approve_code, manager_clear_code):
    print("Deploying exchange manager application...")

    create_manager_transaction = transaction.ApplicationCreateTxn(
        sender=DEVELOPER_ADDRESS,
        sp=algod_client.suggested_params(),
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=manager_approve_code,
        clear_program=manager_clear_code,
        global_schema=transaction.StateSchema(num_uints=0, num_byte_slices=1),
        local_schema=transaction.StateSchema(num_uints=10, num_byte_slices=0)
    ).sign(DEVELOPER_PRIVATE_KEY)

    tx_id = algod_client.send_transaction(create_manager_transaction)
    manager_app_id = wait_for_transaction(tx_id)['created-application-index']
    print(
        f"Exchange Manager deployed with Application ID: {manager_app_id} (Txn ID: https://testnet.algoexplorer.io/tx/{tx_id})"
    )

    print()

    return manager_app_id

#manager_approve_code, manager_clear_code = compile_manager()
#manager_app_id = deploy_exchange_manager(manager_approve_code, manager_clear_code)

compile_manager()


