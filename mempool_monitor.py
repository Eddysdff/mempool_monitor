from web3 import Web3
import json
import asyncio
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='mempool_monitor.log'
)

# 使用 Lava RPC WebSocket 连接
# Lava 提供的 WebSocket URL 格式类似：
WS_URL = "wss://g.w.lavanet.xyz:443/gateway/eth/rpc/e51c4e4c205e66737ffdacc87205576f"  # 替换为你的 Lava WebSocket URL

# 或者使用 HTTP 连接
# HTTP_URL = "https://g.w.lavanet.xyz:443/gateway/eth/json-rpc/你的API_KEY"
# w3 = Web3(Web3.HTTPProvider(HTTP_URL))

w3 = Web3(Web3.LegacyWebSocketProvider(WS_URL))

# Uniswap V2 Factory 地址
UNISWAP_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
# WETH 地址
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

# Uniswap V2 Factory ABI（只包含我们需要的事件）
FACTORY_ABI = json.loads('''[
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"token0","type":"address"},
    {"indexed":true,"internalType":"address","name":"token1","type":"address"},
    {"indexed":false,"internalType":"address","name":"pair","type":"address"},
    {"indexed":false,"internalType":"uint256","name":"","type":"uint256"}],
    "name":"PairCreated","type":"event"}
]''')

async def handle_event(event):
    """处理新配对创建事件"""
    token0 = event['args']['token0']
    token1 = event['args']['token1']
    pair = event['args']['pair']
    
    # 检查是否与WETH配对
    if token0 == WETH or token1 == WETH:
        new_token = token1 if token0 == WETH else token0
        try:
            # 尝试获取代币信息
            token_contract = w3.eth.contract(
                address=new_token,
                abi=json.loads('''[
                    {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},
                    {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},
                    {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}
                ]''')
            )
            
            name = token_contract.functions.name().call()
            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
            
            info = {
                "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "代币名称": name,
                "代币符号": symbol,
                "小数位": decimals,
                "代币地址": new_token,
                "交易对地址": pair
            }
            
            logging.info(f"发现新代币: {json.dumps(info, ensure_ascii=False)}")
            print(f"🚨 新代币上市提醒:\n{json.dumps(info, indent=2, ensure_ascii=False)}")
            
        except Exception as e:
            logging.error(f"获取代币信息失败: {str(e)}")

async def log_loop(event_filter):
    """监听新事件"""
    while True:
        try:
            for event in event_filter.get_new_entries():
                await handle_event(event)
            await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"监听错误: {str(e)}")
            await asyncio.sleep(5)

async def connect_with_retry():
    """带重试机制的连接函数"""
    while True:
        try:
            # 创建合约实例
            factory_contract = w3.eth.contract(
                address=UNISWAP_FACTORY,
                abi=FACTORY_ABI
            )
            
            # 创建事件过滤器
            event_filter = factory_contract.events.PairCreated.create_filter(from_block='latest')
            print("成功连接到以太坊网络")
            return event_filter
        except Exception as e:
            print(f"连接失败，5秒后重试: {str(e)}")
            await asyncio.sleep(5)

async def main():
    """主函数"""
    print("开始监听新币上市...")
    
    while True:
        try:
            event_filter = await connect_with_retry()
            await log_loop(event_filter)
        except Exception as e:
            logging.error(f"主循环错误: {str(e)}")
            print(f"发生错误，正在重新连接: {str(e)}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("监听已停止")
