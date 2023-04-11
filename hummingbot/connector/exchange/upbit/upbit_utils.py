from decimal import Decimal
from typing import Any, Dict

from pydantic import Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap, ClientFieldData
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

CENTRALIZED = True
EXAMPLE_PAIR = "ZRX-ETH"

DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.001"),
    taker_percent_fee_decimal=Decimal("0.001"),
    buy_percent_fee_deducted_from_returns=True
)


def is_exchange_information_valid(exchange_info: Dict[str, Any]) -> bool:
    """
    Verifies if a trading pair is enabled to operate with based on its exchange information
    :param exchange_info: the exchange information for a trading pair
    :return: True if the trading pair is enabled, False otherwise
    """
    return exchange_info.get("status", None) == "TRADING" and "SPOT" in exchange_info.get("permissions", list())


class UpbitConfigMap(BaseConnectorConfigMap):
    connector: str = Field(default="upbit", const=True, client_data=None)
    upbit_api_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Upbit API key",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )
    upbit_api_secret: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Upbit API secret",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )

    class Config:
        title = "upbit"


KEYS = UpbitConfigMap.construct()

OTHER_DOMAINS = ["upbit"]
OTHER_DOMAINS_PARAMETER = {"upbit": "kr"}
OTHER_DOMAINS_EXAMPLE_PAIR = {"upbit": "BTC-USDT"}
OTHER_DOMAINS_DEFAULT_FEES = {"upbit": DEFAULT_FEES}


class UpbitUSConfigMap(BaseConnectorConfigMap):
    connector: str = Field(default="upbit", const=True, client_data=None)
    upbit_api_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Upbit US API key",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )
    upbit_api_secret: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Upbit API secret",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )

    class Config:
        title = "upbit"


OTHER_DOMAINS_KEYS = {"Upbit": UpbitConfigMap.construct()}
