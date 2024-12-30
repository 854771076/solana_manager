import time
import os
from utils.Close_tokenAccount import close_token_account
from solders.keypair import Keypair
from spl.token.core import MINT_LAYOUT, ACCOUNT_LAYOUT
from typing import *
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.api import Client
from spl.token.instructions import transfer_checked, get_associated_token_address, TransferCheckedParams
from spl.token.instructions import (
    create_associated_token_account,
    transfer as token_transfer_instruction,
    TransferParams as token_transferParams,
)
from spl.token.constants import TOKEN_PROGRAM_ID
import math
import asyncio
import random
import base58
from data.config import RPC_URLS
from utils import logger
from solders.system_program import transfer, TransferParams
from solders.transaction import Transaction
LAMPORTS_PER_SOL=1e9
# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)
async def get_token_balance(
    connection: AsyncClient, wallet_address: Pubkey, token_mint_address: Pubkey
) -> dict:
    """
    获取指定代币账户的余额
    """
    token_account_address = get_associated_token_address(
         wallet_address,token_mint_address
    )
    account_info = await connection.get_account_info(token_account_address)

    if not hasattr(account_info.value, "data"):
        raise Exception(f"Token account for {token_account_address} not found.")
    # 解码账户信息并返回余额
    decoded_data = ACCOUNT_LAYOUT.parse(account_info.value.data)
    token_info = await get_token_info(connection, token_mint_address)
    decimals = token_info.decimals
    return {"balance": decoded_data.amount, "decimals": decimals}
async def create_associated_token_account_if_needed(
    connection: AsyncClient,
    keypair: Keypair,
    pubkey: Pubkey,
    token_mint_address: Pubkey,
) -> Pubkey:
    """
    如果没有关联代币账户则创建一个
    """
    associated_token_account =  get_associated_token_address(
        pubkey,token_mint_address
    )
    account_info = await connection.get_account_info(associated_token_account)
    if not hasattr(account_info.value, "data"):
        logger.info(
            f"msg:关联代币账户不存在，正在创建关联代币账户-pubkey:{pubkey.__str__()}-token_mint_address:{token_mint_address.__str__()}"
        )
        # 创建交易以创建关联代币账户
        recent_blockhash = await get_recent_blockhash(connection)
        instructions = create_associated_token_account(
            keypair.pubkey(), pubkey, token_mint_address
        )
        transaction = Transaction.new_signed_with_payer(
            [instructions], keypair.pubkey(), [keypair], recent_blockhash
        )
        # 发送并确认交易
        signature = await connection.send_transaction(transaction)
        # 确认交易
        await connection.confirm_transaction(signature.value, "confirmed")
        logger.info(
            f"msg:关联代币账户已创建-pubkey:{pubkey.__str__()}-token_mint_address:{token_mint_address.__str__()}-{{signature.value}}"
        )
    else:
        logger.debug(
            f"msg:关联代币账户已存在-pubkey:{pubkey.__str__()}-token_mint_address:{token_mint_address.__str__()}"
        )
    return associated_token_account
def getKeypair(privateKey:Union[List[int],str]):
    if isinstance(privateKey,list):
        return Keypair.from_bytes(privateKey)
    elif (privateKey.find('[')!=-1 and privateKey.find(']')!=-1):
        privateKey=eval(privateKey)
        return Keypair.from_bytes(privateKey)
    else:
        return Keypair.from_base58_string(privateKey)
async def get_recent_blockhash(connection: AsyncClient):
    response = await connection.get_latest_blockhash()
    # 检查响应结果
    if hasattr(response, "value"):
        blockhash = response.value.blockhash
        return blockhash
    else:
        raise ValueError("get recent blockhash failed")
async def send_sol(client:AsyncClient, sender:Keypair, receiver:Pubkey, amount):
    lamports = int(amount * LAMPORTS_PER_SOL)
    transfer_instruction = transfer(
        TransferParams(
            from_pubkey=sender.pubkey(),
            to_pubkey=receiver,
            lamports=lamports,
        )
    )
    # 创建交易并添加指令
    recent_blockhash = await get_recent_blockhash(client)
    transaction = Transaction.new_signed_with_payer(
        [transfer_instruction],
        sender.pubkey(),
        [sender],
        recent_blockhash,
    )
    # 将交易发送至网络
    signature = await client.send_transaction(transaction)
    return signature.value
async def close_all_token_account_from_addresses(network_url, keys):
    client=Client(network_url)
    for private_key in keys:
        try:
            sender = getKeypair(private_key)
            close_token_account(client,sender)
            logger.success(f"Sender {sender.pubkey()} close token accounts success")
            return True
            
        except Exception as e:
            logger.exception(e)


            return False
async def collect_sol_from_addresses(network_url, recipient, keys):
    async with AsyncClient(network_url) as client:
        total_amount=0
        for private_key in keys:
            try:
                sender = getKeypair(private_key)
                recipient = Pubkey.from_string(recipient)
                balance = await client.get_balance(sender.pubkey())
                amount = int(balance.value)/LAMPORTS_PER_SOL
                rent=0.001
                if amount-rent > 0:
                    
                    signature=await send_sol(client,sender,recipient,amount-rent)
                    total_amount+=amount
                    logger.success(f"Sender {sender.pubkey()} - recipient {recipient} - amount {amount} - signature {signature} is success")
                else:
                    logger.info(f"Sender {sender.pubkey()} has no sol")
            except Exception as e:
                logger.exception(e)

        return total_amount
async def send_sol_to_addresses(params):
    network_url = params['network_url']
    addresses = params['addresses']
    min_amount = params['min_amount']
    max_amount = params['max_amount']
    private_key = params['private_key']

    logger.info(f"Starting SOL transfer. Network URL: {network_url}")

    start_time = time.time()
    total_sol_sent = 0

    async with AsyncClient(network_url) as client:
        try:
            sender = getKeypair(private_key)
            logger.info(f"Sender public key: {sender.pubkey()}")
        except Exception as e:
            logger.exception(f"Error decoding private key: {e}")
            return {'total_attempts': 0, 'successful_sends': 0, 'total_sol_sent': 0, 'duration': 0}

        total_attempts = 0
        successful_sends = 0
        
        for address in addresses:
            success = False
            attempts = 0
            while not success and attempts < 3:
                attempts += 1
                total_attempts += 1
                amount = random.uniform(min_amount, max_amount)
                try:
                    logger.info(f"Attempting to send {amount} SOL to {address}")
                    recipient = Pubkey.from_string(address)
                    signature = await send_sol(client, sender, recipient, amount)
                    success = True
                    successful_sends += 1
                    total_sol_sent += amount

                    solscan_url = f"https://solscan.io/tx/{signature.value}"

                    logger.info(f"Successfully sent {amount} SOL to {address}. {solscan_url} Signature: {signature.value}")
                except Exception as e:
                    logger.exception(f"Error sending SOL to {address}: {e}")
                    await asyncio.sleep(1)

    end_time = time.time()
    duration = end_time - start_time

    logger.info(f"SOL transfer completed. Total attempts: {total_attempts}, Successful sends: {successful_sends}")
    return {
        'total_attempts': total_attempts,
        'successful_sends': successful_sends,
        'total_sol_sent': total_sol_sent,
        'duration': duration
    }
    

async def get_token_info(connection: AsyncClient, mint_pubkey: Pubkey):
    """
    获取 Solana Token 的 Mint 信息，例如 decimals
    :param connection: AsyncClient 实例
    :param mint_pubkey: 代币的 Mint Pubkey
    :return: 解码后的 Mint 信息字典
    """
    # 获取 Mint Account 的信息
    mint_info_resp = await connection.get_account_info(mint_pubkey)
    if not hasattr(mint_info_resp, "value"):
        raise ValueError("Token mint account not found")
    if not hasattr(mint_info_resp.value, "data"):
        raise ValueError("Token mint account not found")
    # 解析账户数据
    mint_data = mint_info_resp.value.data
    decoded_mint = MINT_LAYOUT.parse(mint_data)
    # 返回代币的 decimals 信息及其他信息
    return decoded_mint

async def transfer_tokens(
    connection: AsyncClient,
    sender_keypair: Keypair,
    receiver_pubkey: Pubkey,
    token_mint_address: Pubkey,
    amount: int,
) -> dict:
    """
    执行代币转账
    """
    balance_resp = await connection.get_balance(sender_keypair.pubkey())
    balance = balance_resp.value / LAMPORTS_PER_SOL
    assert (
        balance > 0
    ), f"pubkey:{sender_keypair.pubkey().__str__()}-SOL余额不足, 当前余额: {balance:.9f} SOL"
    sender_token_account =get_associated_token_address(
        sender_keypair.pubkey(),token_mint_address
    )
    sender_balance_data = await get_token_balance(
        connection, sender_keypair.pubkey(), token_mint_address
    )
    sender_balance = sender_balance_data["balance"]
    token_decimals = sender_balance_data["decimals"]

    # 确保余额足够
    assert (
        sender_balance >= amount
    ), f"pubkey:{sender_keypair.pubkey().__str__()}-TOKEN余额不足,余额：{sender_balance},需要：{amount}"
    # 获取接收者的代币账户地址
    receiver_token_account =  get_associated_token_address(
        receiver_pubkey,token_mint_address
    )
    # 创建关联代币账户（如果需要）
    await create_associated_token_account_if_needed(
        connection, sender_keypair, sender_keypair.pubkey(), token_mint_address
    )
    await create_associated_token_account_if_needed(
        connection, sender_keypair, receiver_pubkey, token_mint_address
    )

    # 创建转账指令
    transfer_instruction = token_transfer_instruction(
        token_transferParams(
            TOKEN_PROGRAM_ID,
            sender_token_account,
            receiver_token_account,
            sender_keypair.pubkey(),
            amount,
        )
    )
    recent_blockhash = await get_recent_blockhash(connection)
    # 创建交易
    transaction = Transaction.new_signed_with_payer(
        [transfer_instruction],
        sender_keypair.pubkey(),
        [sender_keypair],
        recent_blockhash,
    )
    # 发送交易
    signature = await connection.send_transaction(transaction)
    # # 确认交易
    # await connection.confirm_transaction(signature.value, "confirmed")
    # # 获取更新后的余额
    # sender_balance = await get_token_balance(
    #     connection, sender_keypair.pubkey(), token_mint_address
    # )
    # receiver_balance = await get_token_balance(
    #     connection, receiver_pubkey, token_mint_address
    # )
    return signature.value
async def collect_tokens_from_addresses(network_url, token_contract, recipient, keys):
    async with AsyncClient(network_url) as client:
        total_tokens = 0
        for private_key in keys:
            try:
                sender = getKeypair(private_key)
                token_pubkey = Pubkey.from_string(token_contract)
                recipient_pubkey = Pubkey.from_string(recipient)
                balance_info=await get_token_balance(client,sender.pubkey(),token_pubkey)
                amount=balance_info.get('balance')
                decimals=balance_info.get('decimals')
                if amount>0:
                    human_readable_amount=amount/pow(10,decimals)
                    signature=await transfer_tokens(client,sender,recipient_pubkey,token_pubkey,amount)
                    total_tokens+=human_readable_amount
                    logger.success(f"Sender {sender.pubkey()} - recipient {recipient} - token_contract {token_contract} - amount {human_readable_amount} - signature {signature} is success")
                else:
                    logger.info(f"Sender {sender.pubkey()} has no tokens")
            except Exception as e:
                logger.exception(e)
        return  total_tokens
async def get_sol_balance(network_url: str, address: str) -> float:
    try:
        async with AsyncClient(network_url) as client:
            pubkey = Pubkey.from_string(address)
            response = await client.get_balance(pubkey)

            if response.value is not None:
                balance_in_sol = response.value / 1e9
                return balance_in_sol
            else:
                raise ValueError("Failed to get balance")
    except Exception as e:
        logger.exception(f"Error getting SOL balance: {e}")
        raise

def load_from_file(filename):
    filepath = os.path.join('data', filename)
    try:
        with open(filepath, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        logger.exception(f"Error: {filepath} not found")
        return []

async def main(main_private_key):
    network_url = RPC_URLS["MAINNET"]
    logger.info("Starting Solana Transfer Tool")
    await asyncio.sleep(0.1)

    while True:
        print("\n=== Solana Transfer Menu ===")
        print("1. Send SOL to multiple addresses")
        print("2. Gather tokens from multiple wallets")
        print("3. close all token accounts from multiple wallets")
        print("4. Gather sol from multiple wallets")
        print("0. Exit")
        
        choice = input("\nEnter your choice (0-4): ")
        
        if choice == "1":
            # logger.info("Selected: Send SOL to multiple addresses")
            addresses = load_from_file('addresses.txt')
            if not addresses:
                logger.exception("addresses.txt not found or is empty")
                continue
                
            private_key = main_private_key
            main_address=str(getKeypair(main_private_key).pubkey())
            print(f'main wallet address: {main_address}')
            print(f'other wallet count: {len(addresses)}')
            min_amount = float(input("Enter minimum SOL amount: "))
            max_amount = float(input("Enter maximum SOL amount: "))
            
            params = {
                'network_url': network_url,
                'addresses': addresses,
                'min_amount': min_amount,
                'max_amount': max_amount,
                'private_key': private_key
            }
            
            result = await send_sol_to_addresses(params)
            print(f"\nTransfer completed:")
            print(f"Successful sends: {result['successful_sends']}/{result['total_attempts']}")
            print(f"Total SOL sent: {result['total_sol_sent']:.4f}")
            
        elif choice == "2":
            # Gather tokens from multiple wallets
            keys = load_from_file('keys.txt')
            if not keys:
                print("Please ensure keys.txt exists with private keys")
                continue
            private_key = main_private_key
            recipient=str(getKeypair(main_private_key).pubkey())
            print(f'recipient wallet address: {recipient}')
            token_contract = input("Enter token contract address: ")
            total_tokens= await collect_tokens_from_addresses(
                network_url, token_contract, recipient, keys
            )
            
            print(f"\nToken collection completed:")
            print(f"Total tokens collected: {total_tokens:.6f}")
        elif choice == "3":
            # Gather tokens from multiple wallets
            keys = load_from_file('keys.txt')
            if not keys:
                print("Please ensure keys.txt exists with private keys")
                continue
            status= await close_all_token_account_from_addresses(
                network_url, keys
            )
            
            print(f"\nclose token accounts completed:")

        elif choice == "4":
            # Gather tokens from multiple wallets
            keys = load_from_file('keys.txt')
            if not keys:
                print("Please ensure keys.txt exists with private keys")
                continue
            private_key = main_private_key
            recipient=str(getKeypair(main_private_key).pubkey())
            print(f'recipient wallet address: {recipient}')
            total_sol= await collect_sol_from_addresses(
                network_url,  recipient, keys
            )
            print(f"Successful transfers close sol") 
            print(f"Total SOL recive: {total_sol:.4f}")
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    # main wallet private_key
    main_private_key:Union[Sequence[int],str]='xxx'
    asyncio.run(main(main_private_key))

# Grass address Grass7B4RdKfBCjTKgSqnXkqjwiGvQyFbuSCUJr3XXjs
