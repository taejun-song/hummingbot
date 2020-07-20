import asyncio
import logging
from typing import Optional, Dict, AsyncIterable

import aiohttp
import ujson
import websockets
from binance.client import Client as BinanceClient
from websockets import ConnectionClosed

from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.logger import HummingbotLogger

BINANCE_USER_STREAM_ENDPOINT = "https://fapi.binance.com/fapi/v1/listenKey"


class BinancePerpetualUserStreamDataSource(UserStreamTrackerDataSource):
    _bpusds_logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._bpusds_logger is None:
            cls._bpusds_logger = logging.getLogger(__name__)
        return cls._bpusds_logger

    @property
    def last_recv_time(self) -> float:
        return self._last_recv_time

    def __init__(self, binance_client: BinanceClient):
        super().__init__()
        self._binance_client: BinanceClient = binance_client
        self._current_listen_key = None
        self._listen_for_user_stream_task = None
        self._last_recv_time: float = 0

    async def get_listen_key(self):
        async with aiohttp.ClientSession() as client:
            async with client.post(BINANCE_USER_STREAM_ENDPOINT,
                                   headers={"X-MBX-APIKEY": self._binance_client.API_KEY}) as response:
                response: aiohttp.ClientResponse = response
                if response.status != 200:
                    raise IOError(f"Error fetching Binance Perpetual user stream listen key. "
                                  f"HTTP status is {response.status}.")
                data: Dict[str, str] = await response.json()
                return data["listenKey"]

    async def ping_listen_key(self, listen_key: str) -> bool:
        async with aiohttp.ClientSession() as client:
            async with client.put(BINANCE_USER_STREAM_ENDPOINT,
                                  headers={"X-MBX-APIKEY": self._binance_client.API_KEY},
                                  params={"listenKey": listen_key}) as response:
                data: [str, any] = await response.json()
                if "code" in data:
                    self.logger().warning(f"Failed to refresh the listen key {listen_key}: {data}")
                    return False
                return True

    async def ws_messages(self, client: websockets.WebsocketClientProtocol) -> AsyncIterable[str]:
        try:
            while True:
                try:
                    raw_msg: str = await asyncio.wait_for(client.recv(), timeout=30.0)
                    yield raw_msg
                except asyncio.TimeoutError:
                    try:
                        pong_waiter = await client.ping()
                        await asyncio.wait_for(pong_waiter, timeout=10.0)
                    except asyncio.TimeoutError:
                        raise
        except asyncio.TimeoutError:
            self.logger().warning("Websocket ping timed out. Going to reconnect... ")
            return
        except ConnectionClosed:
            return
        finally:
            await client.close()

    async def log_user_stream(self, output: asyncio.Queue):
        while True:
            try:
                stream_url: str = f"wss://fstream.binance.com/ws/{self._current_listen_key}"
                async with websockets.connect(stream_url) as ws:
                    ws: websockets.WebSocketClientProtocol = ws
                    async for raw_msg in self.ws_messages(ws):
                        msg_json: Dict[str, any] = ujson.loads(raw_msg)
                        output.put_nowait(msg_json)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().error("Unexpected error. Retrying after 5 seconds... ", exc_info=True)
                await asyncio.sleep(5)

    async def listen_for_user_stream(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue):
        try:
            while True:
                try:
                    if self._current_listen_key is None:
                        self._current_listen_key = await self.get_listen_key()
                        self.logger().debug(f"Obtained listen key {self._current_listen_key}.")
                        if self._listen_for_user_stream_task is not None:
                            self._listen_for_user_stream_task.cancel()
                        self._listen_for_user_stream_task = safe_ensure_future(self.log_user_stream(output))
                        await self.wait_til_next_tick(seconds=60)
                    success: bool = await self.ping_listen_key(self._current_listen_key)
                    if not success:
                        self._current_listen_key = None
                        if self._listen_for_user_stream_task is not None:
                            self._listen_for_user_stream_task.cancel()
                            self._listen_for_user_stream_task = None
                        continue
                    self.logger().debug(f"Refreshed listen key {self._current_listen_key}.")
                    await self.wait_til_next_tick(seconds=60)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    self.logger().error("Unexpected error while maintaning the user event listen key. Retrying after "
                                        "5 seconds...", exc_info=True)
                    await asyncio.sleep(5)
        finally:
            if self._listen_for_user_stream_task is not None:
                self._listen_for_user_stream_task.cancel()
                self._listen_for_user_stream_task = None
            self._current_listen_key = None
