
![image](https://github.com/user-attachments/assets/d0c6bd32-15ca-4575-80bd-e7b4a1dee68b)

2. Configure RPC URL:
   - Open `data/config.py`
   - Replace the RPC URL with your own from [Chainstack](https://chainstack.com/) or use default:
   ```python
   RPC_URLS = {
       "MAINNET": "your_rpc_url_here",
   }
   ```

3. Prepare wallet files in `data` folder:
   - For sending SOL: Create `data/addresses.txt` with recipient addresses
   - For gathering tokens: Create `data/keys.txt` with private keys

Example files:

## Using the Tool

### Starting the Tool
### Menu Options

#### 1. Send SOL to Multiple Addresses
1. Choose option `1`
2. Enter:
   - Sender's private key
   - Minimum SOL amount (e.g., 0.1)
   - Maximum SOL amount (e.g., 0.2)
3. Tool will:
   - Send random amounts between min/max to each address
   - Show transaction links on Solscan
   - Display success rate and total SOL sent

#### 2. Gather Tokens from Multiple Wallets
1. Choose option `2`
2. Enter:
   - Token contract address (e.g., USDC: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v)
   - Recipient address
3. Tool will:
   - Check token balances
   - Transfer all tokens to recipient
   - Show transfer results

#### 3. Exit
- Choose option `3` to close the program

## Common Token Addresses
- USDC: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

## Monitoring
- Check console for real-time progress
- Review `logs/solana_transfer.log` for detailed logs
- Use Solscan links to verify transactions

## Troubleshooting

1. "addresses.txt not found":
   - Create `data/addresses.txt`
   - Add addresses (one per line)

2. "Error decoding private key":
   - Check private key format
   - Ensure it's in base58 format

3. "Insufficient balance":
   - Add SOL to sender wallet
   - Check recipient token accounts

4. RPC errors:
   - Verify RPC URL in config.py
   - Try backup RPC URL

## Security Notes
- Never share private keys
- Keep keys.txt secure
- Test with small amounts first
- Double-check addresses before sending