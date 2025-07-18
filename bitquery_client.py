import asyncio
import json
import aiohttp
import websockets
from typing import Dict, Any, Optional, List
from config import BITQUERY_API_KEY, BITQUERY_GRAPHQL_URL, BITQUERY_WEBSOCKET_URL

class BitqueryClient:
    def __init__(self):
        self.api_key = BITQUERY_API_KEY
        self.graphql_url = BITQUERY_GRAPHQL_URL
        self.websocket_url = BITQUERY_WEBSOCKET_URL
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a GraphQL query"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        async with self.session.post(self.graphql_url, json=payload, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Query failed with status {response.status}: {await response.text()}")
    
    async def get_bonding_curve_progress(self, token_mint: str) -> Optional[Dict[str, Any]]:
        """Get bonding curve progress for a token"""
        query = """
        query GetBondingCurveProgress($token: String!) {
          Solana {
            DEXPools(
              where: {
                Pool: {
                  Market: {
                    BaseCurrency: {
                      MintAddress: { is: $token }
                    }
                  }
                  Dex: {
                    ProgramAddress: { is: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P" }
                  }
                }
              }
              orderBy: { descending: Block_Slot }
              limit: { count: 1 }
            ) {
              Pool {
                Market {
                  MarketAddress
                  BaseCurrency {
                    MintAddress
                    Symbol
                    Name
                  }
                  QuoteCurrency {
                    MintAddress
                    Symbol
                    Name
                  }
                }
                Dex {
                  ProtocolFamily
                  ProtocolName
                }
                Quote {
                  PostAmount
                  PriceInUSD
                  PostAmountInUSD
                }
                Base {
                  PostAmount
                }
              }
            }
          }
        }
        """
        
        variables = {"token": token_mint}
        result = await self.execute_query(query, variables)
        
        if result.get('data', {}).get('Solana', {}).get('DEXPools'):
            pools = result['data']['Solana']['DEXPools']
            if pools:
                return pools[0]
        return None
    
    async def get_token_price(self, token_mint: str) -> Optional[Dict[str, Any]]:
        """Get latest token price"""
        query = """
        query GetTokenPrice($token: String!) {
          Solana {
            DEXTradeByTokens(
              limit: { count: 1 }
              orderBy: { descending: Block_Time }
              where: {
                Trade: {
                  Currency: { MintAddress: { is: $token } }
                  Dex: {
                    ProgramAddress: { is: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P" }
                  }
                }
                Transaction: { Result: { Success: true } }
              }
            ) {
              Block {
                Time
              }
              Trade {
                Currency {
                  Name
                  MintAddress
                  Symbol
                }
                Amount
                AmountInUSD
                Price
                PriceInUSD
              }
            }
          }
        }
        """
        
        variables = {"token": token_mint}
        result = await self.execute_query(query, variables)
        
        if result.get('data', {}).get('Solana', {}).get('DEXTradeByTokens'):
            trades = result['data']['Solana']['DEXTradeByTokens']
            if trades:
                return trades[0]
        return None
    
    async def get_tokens_by_market_cap_range(self, min_price: float, max_price: float) -> List[Dict[str, Any]]:
        """Get tokens within a specific market cap range"""
        query = """
        subscription GetTokensByMarketCap($minPrice: Float!, $maxPrice: Float!) {
          Solana {
            DEXTradeByTokens(
              where: {
                Trade: {
                  PriceInUSD: { gt: $minPrice, lt: $maxPrice }
                  Dex: {
                    ProgramAddress: { is: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P" }
                  }
                  Side: {
                    Currency: {
                      MintAddress: { is: "11111111111111111111111111111111" }
                    }
                  }
                }
                Transaction: { Result: { Success: true } }
              }
            ) {
              Block {
                Time
              }
              Trade {
                Currency {
                  Name
                  Symbol
                  Decimals
                  MintAddress
                }
                Price
                PriceInUSD
                Dex {
                  ProtocolName
                  ProtocolFamily
                  ProgramAddress
                }
                Side {
                  Currency {
                    MintAddress
                    Name
                    Symbol
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {"minPrice": min_price, "maxPrice": max_price}
        result = await self.execute_query(query, variables)
        
        if result.get('data', {}).get('Solana', {}).get('DEXTradeByTokens'):
            return result['data']['Solana']['DEXTradeByTokens']
        return []
    
    async def get_tokens_above_bonding_curve_threshold(self, min_progress: float) -> List[Dict[str, Any]]:
        """Get tokens above a certain bonding curve progress threshold"""
        # Calculate the balance range for the bonding curve progress
        # Formula: BondingCurveProgress = 100 - (((balance - 206900000) * 100) / 793100000)
        # Rearranged: balance = 206900000 + (793100000 * (100 - progress) / 100)
        
        max_balance = 206900000 + (793100000 * (100 - min_progress) / 100)
        
        query = """
        subscription GetTokensAboveBondingCurve($maxBalance: String!) {
          Solana {
            DEXPools(
              where: {
                Pool: {
                  Base: { PostAmount: { gt: "206900000", lt: $maxBalance } }
                  Dex: {
                    ProgramAddress: { is: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P" }
                  }
                  Market: {
                    QuoteCurrency: {
                      MintAddress: { is: "11111111111111111111111111111111" }
                    }
                  }
                }
                Transaction: { Result: { Success: true } }
              }
            ) {
              Pool {
                Market {
                  BaseCurrency {
                    MintAddress
                    Name
                    Symbol
                  }
                  MarketAddress
                  QuoteCurrency {
                    MintAddress
                    Name
                    Symbol
                  }
                }
                Dex {
                  ProtocolName
                  ProtocolFamily
                }
                Base {
                  PostAmount
                }
                Quote {
                  PostAmount
                  PriceInUSD
                  PostAmountInUSD
                }
              }
            }
          }
        }
        """
        
        variables = {"maxBalance": str(int(max_balance))}
        result = await self.execute_query(query, variables)
        
        if result.get('data', {}).get('Solana', {}).get('DEXPools'):
            return result['data']['Solana']['DEXPools']
        return []
    
    async def subscribe_to_real_time_trades(self, token_mint: str, callback):
        """Subscribe to real-time trades for a token"""
        subscription = """
        subscription TradeSubscription($token: String!) {
          Solana {
            DEXTradeByTokens(
              where: {
                Trade: {
                  Currency: { MintAddress: { is: $token } }
                  Dex: {
                    ProgramAddress: { is: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P" }
                  }
                }
                Transaction: { Result: { Success: true } }
              }
            ) {
              Block {
                Time
              }
              Trade {
                Currency {
                  MintAddress
                  Name
                  Symbol
                }
                Dex {
                  ProtocolName
                  ProtocolFamily
                  ProgramAddress
                }
                Side {
                  Currency {
                    MintAddress
                    Symbol
                    Name
                  }
                }
                Price
                PriceInUSD
              }
              Transaction {
                Signature
              }
            }
          }
        }
        """
        
        variables = {"token": token_mint}
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'type': 'start',
            'payload': {
                'query': subscription,
                'variables': variables
            }
        }
        
        try:
            async with websockets.connect(
                self.websocket_url,
                extra_headers=headers,
                subprotocols=['graphql-ws']
            ) as websocket:
                # Send connection init
                await websocket.send(json.dumps({'type': 'connection_init'}))
                
                # Wait for connection ack
                response = await websocket.recv()
                init_response = json.loads(response)
                
                if init_response.get('type') == 'connection_ack':
                    # Send subscription
                    await websocket.send(json.dumps(payload))
                    
                    # Listen for messages
                    async for message in websocket:
                        data = json.loads(message)
                        if data.get('type') == 'data':
                            await callback(data.get('payload'))
                            
        except Exception as e:
            print(f"WebSocket error: {e}")
    
    def calculate_bonding_curve_progress(self, balance: int) -> float:
        """Calculate bonding curve progress from balance"""
        # Formula: BondingCurveProgress = 100 - (((balance - 206900000) * 100) / 793100000)
        if balance <= 206900000:
            return 100.0
        
        progress = 100 - (((balance - 206900000) * 100) / 793100000)
        return max(0.0, min(100.0, progress))
    
    def calculate_market_cap(self, price_usd: float) -> float:
        """Calculate market cap from USD price"""
        # Market cap = price * total supply (1 billion tokens)
        return price_usd * 1000000000