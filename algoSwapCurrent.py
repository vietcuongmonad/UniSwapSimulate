from pyteal import *

'''
    Manager need to store some info about each Escrow contract
        => each escrow contract opt into manager & store field in
        manager's local storage:

    TOKEN1 & TOKEN2: asset ID's of Token 1 & Token 2
    LIQUIDITY_TOKEN: asset ID of liquidity token for this escrow contract
    TOKEN1_BAL & TOKEN2_BAL: total amount of token1 & token 2 currently
        in liquidity pool
        -> Different from getting the Escrow contract's balance for TOKEN1
            & TOKEN2 because user's real balances include USER_TOKEN1_UNUSED
            & USER_TOKEN2_UNUSED
    LIQUIDITY_TOKEN_DISTRIBUTED: total amount of LIQUIDITY_TOKEN distributed
        to user
    PROTOCOL_UNUSED_TOKEN1 & PROTOCOL_UNUSED_TOKEN2: for protocol fee,
        withdrawable by dev, set to 0.05%. Swap fee = 0.45%
'''

TOKEN1 = Bytes("T1")
TOKEN2 = Bytes("T2")
LIQUIDITY_TOKEN = Bytes("LT")
TOKEN1_BAL = Bytes("B1")
TOKEN2_BAL = Bytes("B2")
LIQUIDITY_TOKEN_DISTRIBUTED = Bytes("LD")
USER_UNUSED_TOKEN1 = Bytes("U1")
USER_UNUSED_TOKEN2 = Bytes("U2")
USER_UNUSED_LIQUIDITY = Bytes("UL")

def approval_program():
    '''
        This program maintains global & local storage for users &
            escrow contracts that are opted in AlgoSwap protocol for possible
            atomic transactions group that AlgoSwap supports
                - Add Liquidity

        Any atomic transaction group MUST have a transaction to manager
        smart contract as the second transaction of the group to proceed

        Txn.Account index
            Int(0) => sender account
            Int(1) => additional account
    '''

    # Read from additional account
    _token1 = App.localGet(Int(1), TOKEN1)
    _token2 = App.localGet(Int(1), TOKEN2)
    _liquidity_token = App.localGet(Int(1), LIQUIDITY_TOKEN)

    _token1_bal = App.localGet(Int(1), TOKEN1_BAL)
    _token2_bal = App.localGet(Int(1), TOKEN2_BAL)
    _liquidity_token_distributed = App.localGet(Int(1), LIQUIDITY_TOKEN_DISTRIBUTED)

    #_protocol_unused_token1 = App.localGet(Int(1), PROTOCOL_UNUSED_TOKEN1)
    #_protocol_unused_token2 = App.localGet(Int(1), PROTOCOL_UNUSED_TOKEN2)

    # Write to additional account
    def write_token1_bal(bal: Int):
        return App.localPut(Int(1), TOKEN1_BAL, bal)
    def write_token2_bal(bal: Int):
        return App.localPut(Int(1), TOKEN2_BAL, bal)
    def write_liquidity_token_distributed(bal: Int):
        return App.localPut(Int(1), LIQUIDITY_TOKEN_DISTRIBUTED, bal)

    def write_protocol_unused_token1(amount: Int):
        return App.localPut(Int(1), PROTOCOL_UNUSED_TOKEN1, amount)
    def write_protocol_unused_token2(amount: Int):
        return App.localPut(Int(1), PROTOCOL_UNUSED_TOKEN2, amount)

    # Read from sender account
    def read_user_unused_token1(address: Bytes):
        return App.localGet(Int(0), Concat(USER_UNUSED_TOKEN1, address))
    def read_user_unused_token2(address: Bytes):
        return App.localGet(Int(0), Concat(USER_UNUSED_TOKEN2, address))
    def read_user_unused_liquidity(address: Bytes):
        return App.localGet(Int(0), Concat(USER_UNUSED_LIQUIDITY, address))

    # Write to sender account
    def write_user_unused_token1(address: Bytes, amount: Int):
        return App.localPut(Int(0), Concat(USER_UNUSED_TOKEN1, address), amount)
    def write_user_unused_token2(address: Bytes, amount: Int):
        return App.localPut(Int(0), Concat(USER_UNUSED_TOKEN2, address), amount)
    def write_user_unused_liquidity(address: Bytes, amount: Int):
        return App.localPut(Int(0), Concat(USER_UNUSED_LIQUIDITY, address), amount)

    # Scratch Vars
    sv_token1_used = ScratchVar(TealType.uint64)
    sv_token2_used = ScratchVar(TealType.uint64)
    sv_token1_bal = ScratchVar(TealType.uint64)
    sv_token2_bal = ScratchVar(TealType.uint64)
    sv_liquidity_token_distributed = ScratchVar(TealType.uint64)
    sv_swap_token2_output = ScratchVar(TealType.uint64)
    sv_swap_token1_output = ScratchVar(TealType.uint64)
    sv_token1_available = ScratchVar(TealType.uint64)
    sv_token2_available = ScratchVar(TealType.uint64)
    sv_new_liquidity = ScratchVar(TealType.uint64)
    sv_temp = ScratchVar(TealType.uint64)

    on_create = Int(1)
    on_closeout = Int(1)
    on_updateapp = Int(1)
    on_deleteapp = Int(1)

    on_opt_in = If(Txn.application_args.length() == Int(3),
        Seq([
            # init sender'local state as an escrow
            App.localPut(Int(0), LIQUIDITY_TOKEN, Btoi(Txn.application_args[0])),
            App.localPut(Int(0), TOKEN1, Btoi(Txn.application_args[1])),
            App.localPut(Int(0), TOKEN2, Btoi(Txn.application_args[2])),
            Int(1)
        ]),
        Int(1)
    )

    '''
        Must ensure exchange rate (TOKEN1_BAL / TOKEN2_BAL)
        => if deposit: (TOKEN1_BAL + token1_deposit) / (tOKEN2_BAL + token2_deposit)
        => can calculate token deposit base on each other to ensure

        If LIQUIDITY_TOKEN_DISTRIBUTED = 0 => 1st liquidity provider
        => advise to deposit amount of token1 & token2 that are equal value
        on other exchanges
        => E.g.: send x of token 1, need to send x / TOKEN1_BAL * TOKEN2_BAL token2

        Due to slippage, Users cannot send exact amount
        => min(token1_deposit, token2 * TOKEN1_BAL/TOKEN2_BAL) of Token1
        & min(token2_deposit, token1 * TOKEN1_BAL/TOKEN2_BAL) of Token2
        are made available in liquidity pool, & the rest is all
        refundable to sender
    '''
    on_add_liquidity = Seq([
        sv_token1_bal.store(_token1_bal),
        sv_token2_bal.store(_token2_bal),
        sv_liquidity_token_distributed.store(_liquidity_token_distributed),
        If(
            sv_liquidity_token_distributed.load() == Int(0),
            # Then, token1_used = token1_deposit
            # token2_used = token2_deposit
            # new_liquidity = token1_deposit
            Seq([
                sv_token1_used.store(Gtxn[2].asset_amount()),
                sv_token2_used.store(Gtxn[3].asset_amount()),
                sv_new_liquidity.store(Gtxn[2].asset_amount())
            ]),
            # Else, token1_used =
            #         min(token1_deposit, token2_deposit / TOKEN2_BAL * TOKEN1_BAL)
            #         , token2_used =
            #         min(token2_deposit, token1_deposit / TOKEN1_BAL * TOKEN2_BAL)
            Seq([
                sv_temp.store(Gtxn[3].asset_amount() / sv_token2_bal.load() * sv_token1_bal.load()),
                If(
                    Gtxn[2].asset_amount() < sv_temp.load(), # token1_deposit is min
                    sv_token1_used.store(Gtxn[2].asset_amount()),
                    sv_token1_used.store(sv_temp.load())
                ),
                sv_temp.store(Gtxn[2].asset_amount() / sv_token1_bal.load() * sv_token2_bal.load()),
                If(
                    Gtxn[3].asset_amount() < sv_temp.load(), # token2_deposit is min
                    sv_token2_used.store(Gtxn[3].asset_amount()),
                    sv_token2_used.store(sv_temp.load())
                ),
                sv_new_liquidity.store(sv_liquidity_token_distributed.load() * Gtxn[2].asset_amount()
                    / sv_token1_bal.load()),
            ])
        ),
        # new_liquidity >= min_liquidity_received_from_algoswap
        Assert(sv_new_liquidity.load() >= Btoi(Txn.application_args[1])),
        # USER_UNUSED_TOKEN1 += token1_deposit - sv_token1_used. Likewise, USER_UNUSED_TOKEN2
        write_user_unused_token1(
            Txn.accounts[1],
            read_user_unused_token1(Txn.accounts[1]) + Gtxn[2].asset_amount() - sv_token1_used.load()
        ),
        write_user_unused_token2(
            Txn.accounts[1],
            read_user_unused_token2(Txn.accounts[1]) + Gtxn[3].asset_amount() - sv_token2_used.load()
        ),
        write_user_unused_liquidity(
            Txn.accounts[1],
            read_user_unused_liquidity(Txn.accounts[1]) + sv_new_liquidity.load()
        ),
        #TOKEN1_BAL += token1_used. Likewise, TOKEN2_BAL
        write_token1_bal(sv_token1_bal.load() + sv_token1_used.load()),
        write_token2_bal(sv_token2_bal.load() + sv_token2_used.load()),
        #LIQUIDITY_TOKEN_DISTRIBUTED += new_liquidity
        write_liquidity_token_distributed(sv_liquidity_token_distributed.load() + sv_new_liquidity.load()),
        Int(1)
    ])

    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.CloseOut, on_closeout],
        [Txn.on_completion() == OnComplete.OptIn, on_opt_in],
        [Txn.on_completion() == OnComplete.NoOp, on_add_liquidity],
        [Txn.on_completion() == OnComplete.UpdateApplication, on_updateapp],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_deleteapp],
    )
    return program

def clear_program():
    program = Return(Int(1))
    return program 