import time
import os

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solders.system_program import TransferParams, transfer
from solana.transaction import Transaction
from spl.token.instructions import transfer_checked, get_associated_token_address, TransferCheckedParams
from spl.token.constants import TOKEN_PROGRAM_ID

import asyncio
import random
import base58
from data.config import RPC_URLS
from utils import logger

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)


async def send_sol(client, sender, receiver, amount):
    transaction = Transaction().add(transfer(
        TransferParams(
            from_pubkey=sender.pubkey(),
            to_pubkey=Pubkey.from_string(receiver),
            lamports=int(amount * 1e9)
        )
    ))
    return await client.send_transaction(transaction, sender)


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
            private_key_bytes = base58.b58decode(private_key)
            sender = Keypair.from_bytes(private_key_bytes)
            logger.info(f"Sender public key: {sender.pubkey()}")
        except Exception as e:
            logger.error(f"Error decoding private key: {e}")
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
                    signature = await send_sol(client, sender, address, amount)
                    success = True
                    successful_sends += 1
                    total_sol_sent += amount

                    solscan_url = f"https://solscan.io/tx/{signature.value}"

                    logger.info(f"Successfully sent {amount} SOL to {address}. {solscan_url} Signature: {signature.value}")
                except Exception as e:
                    logger.error(f"Error sending SOL to {address}: {e}")
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


async def get_token_info(network_url, token_contract):
    async with AsyncClient(network_url) as client:
        try:
            token_pubkey = Pubkey.from_string(token_contract)
            token_info = await client.get_token_supply(token_pubkey)
            return {
                'decimals': token_info.value.decimals
            }
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return None


async def collect_tokens_from_addresses(network_url, token_contract, recipient, keys):
    async with AsyncClient(network_url) as client:
        results = []
        total_tokens = 0
        token_info = await get_token_info(network_url, token_contract)
        decimals = token_info['decimals'] if token_info else 0

        for private_key in keys:
            try:
                sender = Keypair.from_bytes(base58.b58decode(private_key))
                token_pubkey = Pubkey.from_string(token_contract)
                recipient_pubkey = Pubkey.from_string(recipient)

                sender_ata = get_associated_token_address(sender.pubkey(), token_pubkey)
                recipient_ata = get_associated_token_address(recipient_pubkey, token_pubkey)

                balance = await client.get_token_account_balance(sender_ata)
                amount = int(balance.value.amount)

                if amount > 0:
                    tx = Transaction().add(
                        transfer_checked(
                            TransferCheckedParams(
                                program_id=TOKEN_PROGRAM_ID,
                                source=sender_ata,
                                mint=token_pubkey,
                                dest=recipient_ata,
                                owner=sender.pubkey(),
                                amount=amount,
                                decimals=decimals
                            )
                        )
                    )

                    signature = await client.send_transaction(tx, sender)

                    total_tokens += amount
                    human_readable_amount = amount / (10 ** decimals)

                    results.append({
                        'success': True,
                        'sender': str(sender.pubkey()),
                        'amount': human_readable_amount,
                        'signature': str(signature)
                    })
                else:
                    logger.info(f"Sender {sender.pubkey()} has no tokens")
                    results.append({
                        'success': False,
                        'sender': str(sender.pubkey()),
                        'error': 'Недостаточно токенов'
                    })
            except Exception as e:
                results.append({
                    'success': False,
                    'sender': str(sender.pubkey()) if 'sender' in locals() else 'Unknown',
                    'error': str(e)
                })

        return results, total_tokens, decimals


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
        logger.error(f"Error getting SOL balance: {e}")
        raise

def load_from_file(filename):
    filepath = os.path.join('data', filename)
    try:
        with open(filepath, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        logger.error(f"Error: {filepath} not found")
        return []

async def main():
    network_url = RPC_URLS["MAINNET"]
    logger.info("Starting Solana Transfer Tool")
    await asyncio.sleep(0.1)

    while True:
        print("\n=== Solana Transfer Menu ===")
        print("1. Send SOL to multiple addresses")
        print("2. Gather tokens from multiple wallets")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == "1":
            # logger.info("Selected: Send SOL to multiple addresses")
            addresses = load_from_file('addresses.txt')
            if not addresses:
                logger.error("addresses.txt not found or is empty")
                continue
                
            private_key = input("Enter sender's private key: ")
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
                
            token_contract = input("Enter token contract address: ")
            recipient = input("Enter recipient address: ")
            
            results, total_tokens, decimals = await collect_tokens_from_addresses(
                network_url, token_contract, recipient, keys
            )
            
            print(f"\nToken collection completed:")
            print(f"Total tokens collected: {total_tokens / (10 ** decimals):.6f}")
            print(f"Successful transfers: {sum(1 for r in results if r['success'])}/{len(results)}")
            
        elif choice == "3":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":

    asyncio.run(main())

# Grass address Grass7B4RdKfBCjTKgSqnXkqjwiGvQyFbuSCUJr3XXjs
