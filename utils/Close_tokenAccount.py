from solana.rpc.commitment import Finalized
from solders.compute_budget import set_compute_unit_price, set_compute_unit_limit
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client
from solana.transaction import Transaction
from solana.rpc import types
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from spl.token.instructions import burn, BurnParams, CloseAccountParams, close_account
from loguru import logger



def get_token_accountsCount(client: Client, wallet_address: Pubkey):
    # try:
        owner = wallet_address
        opts = types.TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
        response = client.get_token_accounts_by_owner(owner, opts)
        return response.value
    # except Exception as e:
    #     return []
# 危险操作，谨慎使用
def close_and_burn_token_account(
    client: Client,
    payer: Keypair,
):
    wallet_address = payer.pubkey()
    response = get_token_accountsCount(client, wallet_address)
    solana_token_accounts = {
        str(token_account.pubkey): token_account for token_account in response
    }
    tokenAccount_list = list(solana_token_accounts.keys())
    while len(tokenAccount_list) > 0:
        try:
            for token in tokenAccount_list:
                burn_instruction = []
                c = client.get_account_info_json_parsed(Pubkey.from_string(token))
                mint_address = Pubkey.from_string(c.value.data.parsed["info"]["mint"])
                token_account = Pubkey.from_string(token)
                balance = client.get_token_account_balance(Pubkey.from_string(token))
                amount = balance.value.amount
                logger.debug(amount)
                params = BurnParams(
                    amount=int(amount),
                    account=token_account,
                    mint=mint_address,
                    owner=payer.pubkey(),
                    program_id=TOKEN_PROGRAM_ID,
                )

                burn_inst = burn(params)
                close_account_params = CloseAccountParams(
                    account=token_account,
                    dest=payer.pubkey(),
                    owner=payer.pubkey(),
                    program_id=TOKEN_PROGRAM_ID,
                )
                transaction = Transaction()
                transaction.add(
                    close_account(close_account_params),
                    set_compute_unit_price(25_232),
                    set_compute_unit_limit(200_337),
                )
                burn_instruction.extend(
                    [
                        burn_inst,
                        transaction.instructions[0],
                        transaction.instructions[1],
                        transaction.instructions[2],
                    ]
                )
                block_hash = client.get_latest_blockhash(commitment=Finalized)
                logger.debug(block_hash.value.blockhash)
                msg = MessageV0.try_compile(
                    payer=payer.pubkey(),
                    instructions=[instruction for instruction in burn_instruction],
                    address_lookup_table_accounts=[],
                    recent_blockhash=block_hash.value.blockhash,
                )
                tx1 = VersionedTransaction(msg, [payer])
                txn_sig = client.send_transaction(tx1)
                logger.debug(txn_sig.value)
                tokenAccount_list.remove(token)
        except Exception as e:
            logger.debug(e)
            continue
def close_token_account_by_token(
    client: Client,
    payer: Keypair,
    mint_address: str,
):
    wallet_address = payer.pubkey()
    try:
        mint_address = Pubkey.from_string(mint_address)
        
        token_account, _ = mint_address.find_program_address(
        [
            wallet_address.__bytes__(),
            TOKEN_PROGRAM_ID.__bytes__(),
            mint_address.__bytes__(),
        ],
        ASSOCIATED_TOKEN_PROGRAM_ID,
        )
        balance = client.get_token_account_balance(token_account)
        amount = balance.value.amount
        logger.debug(f'{token_account} {mint_address},{amount}')
        if int(amount)==0:
            close_account_params = CloseAccountParams(
                account=token_account,
                dest=payer.pubkey(),
                owner=payer.pubkey(),
                program_id=TOKEN_PROGRAM_ID,
            )
            transaction = Transaction()
            transaction.add(
                close_account(close_account_params),
                set_compute_unit_price(25_232),
                set_compute_unit_limit(200_337),
            )

            block_hash = client.get_latest_blockhash(commitment=Finalized)
            logger.debug(block_hash.value.blockhash)
            msg = MessageV0.try_compile(
                payer=payer.pubkey(),
                instructions=[
                transaction.instructions[0],
                transaction.instructions[1],
                transaction.instructions[2],
            ],
                address_lookup_table_accounts=[],
                recent_blockhash=block_hash.value.blockhash,
            )
            tx1 = VersionedTransaction(msg, [payer])
            txn_sig = client.send_transaction(tx1)
            logger.success(f'清除{token_account}成功-tx:{txn_sig.value}')
        else:
            logger.warning(f"{mint_address},余额不为0,amount:{amount}")
    except Exception as e:
        logger.error(e)
def close_token_account(
    client: Client,
    payer: Keypair,
):
    wallet_address = payer.pubkey()
    response = get_token_accountsCount(client, wallet_address)
    solana_token_accounts = {
        str(token_account.pubkey): token_account for token_account in response
    }
    tokenAccount_list = list(solana_token_accounts.keys())
    while len(tokenAccount_list) > 0:
        try:
            for token in tokenAccount_list:
                c = client.get_account_info_json_parsed(Pubkey.from_string(token))
                mint_address = Pubkey.from_string(c.value.data.parsed["info"]["mint"])
                token_account = Pubkey.from_string(token)
                balance = client.get_token_account_balance(Pubkey.from_string(token))
                amount = balance.value.amount
                logger.debug(f'{token},{mint_address},{amount}')
                if int(amount)==0:
                    close_account_params = CloseAccountParams(
                        account=token_account,
                        dest=payer.pubkey(),
                        owner=payer.pubkey(),
                        program_id=TOKEN_PROGRAM_ID,
                    )
                    transaction = Transaction()
                    transaction.add(
                        close_account(close_account_params),
                        set_compute_unit_price(25_232),
                        set_compute_unit_limit(200_337),
                    )

                    block_hash = client.get_latest_blockhash(commitment=Finalized)
                    logger.debug(block_hash.value.blockhash)
                    msg = MessageV0.try_compile(
                        payer=payer.pubkey(),
                        instructions=[
                        transaction.instructions[0],
                        transaction.instructions[1],
                        transaction.instructions[2],
                    ],
                        address_lookup_table_accounts=[],
                        recent_blockhash=block_hash.value.blockhash,
                    )
                    tx1 = VersionedTransaction(msg, [payer])
                    txn_sig = client.send_transaction(tx1)
                    logger.debug(txn_sig.value)
                else:
                    logger.warning(f"{mint_address},balance not zero,amount:{amount}")
                tokenAccount_list.remove(token)
        except Exception as e:
            logger.debug(e)
            continue

