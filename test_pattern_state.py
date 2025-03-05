import time
from abc import ABC, abstractmethod
from lib2to3.fixes.fix_input import context
from typing import Dict, Set
import asyncio

from utils.logger import logger


class TokenManager:
    def __init__(self, list_tokens: Dict[str, dict]):
        self.list_tokens = list_tokens
        self.cooldown_tokens: Set[str] = set()
        self.current_tokens_with_spread: Dict[str, float] = {}

    def get_tokens(self) -> Dict[str, dict]:
        """Возвращает токены, которые не находятся в кудоуне."""
        return {k: v for k, v in self.list_tokens.items() if k not in self.cooldown_tokens}

    async def add_to_cooldown(self, token: str, cooldown_time: int):
        """Добавляет токен в cooldown на указанное время."""
        self.cooldown_tokens.add(token)
        await asyncio.sleep(cooldown_time)
        self.cooldown_tokens.remove(token)
        logger.info(f"[INFO] {token} is back in rotation")

    def update_spread(self, token: str, spread: float):
        """Обновляет спред для токена."""
        self.current_tokens_with_spread[token] = spread

    def remove_spread(self, token: str):
        """Удаляет токен из списка текущих спредов."""
        self.current_tokens_with_spread.pop(token, None)

    def get_current_spread(self, token: str) -> float:
        """Возвращает текущий спред для токена."""
        return self.current_tokens_with_spread.get(token, 0.0)

    def is_token_in_history(self, token: str) -> bool:
        """Проверяет наличие токена в истории."""
        return token in self.current_tokens_with_spread


# Pattern State


class SpreadState(ABC):
    def __init__(self, context):  # context: SpreadContext
        self.context = context

    @abstractmethod
    def handle_spread(self, token: str, spread: float, minimum_spread: float,
                      token_manager: TokenManager) -> bool | dict:
        pass


class SpreadContext:
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
        self._state: SpreadState = HasSpreadState(self)

    def transition_to(self, state: SpreadState):
        self._state = state

    def handle_spread(self, token: str, spread: float, minimum_spread: float) -> dict:
        result = self._state.handle_spread(token, spread, minimum_spread, self.token_manager)
        return result


class HasSpreadState(SpreadState):
    def handle_spread(self, token: str, spread: float, minimum_spread: float,
                      token_manager: TokenManager) -> bool | dict:
        if token_manager.is_token_in_history(token):
            self.context.transition_to(CheckSpreadAvailableState(self.context))
            return self.context.handle_spread(token, spread, minimum_spread)
        if spread >= 30:
            token_manager.update_spread(token, spread)
            return {"Has_spread": True, "thread_id": None}
        if spread > minimum_spread:
            token_manager.update_spread(token, spread)
            return {"Has_spread": True, "thread_id": None}
        return {"Has_spread": False, "thread_id": None}


class CheckSpreadAvailableState(SpreadState):
    def handle_spread(self, token: str, spread: float, minimum_spread: float,
                      token_manager: TokenManager) -> bool | dict:
        current_spread = token_manager.get_current_spread(token)

        if spread >= 30:
            self.context.transition_to(SpreadLifeChangeState(self.context))
            return self.context.handle_spread(token, spread, minimum_spread)
        elif spread < minimum_spread:
            token_manager.remove_spread(token)
            return {"Has_spread": False, "thread_id": None}
        elif spread > current_spread + 4:
            token_manager.update_spread(token, spread)
            # self.context.transition_to(SpreadIncreasedState(self.context))
            return {"Has_spread": True, "thread_id": None}
        elif spread < current_spread - 4:
            token_manager.update_spread(token, spread)
            # self.context.transition_to(SpreadDecreasedState(self.context))
            return {"Has_spread": True, "thread_id": None}

        token_manager.update_spread(token, spread)
        return {"Has_spread": False, "thread_id": None}


class SpreadLifeChangeState(SpreadState):
    def handle_spread(self, token: str, spread: float, minimum_spread: float,
                      token_manager: TokenManager) -> bool | dict:
        current_spread = token_manager.get_current_spread(token)

        if spread < minimum_spread:
            token_manager.remove_spread(token)
            return {"Has_spread": False, "thread_id": None}
        elif spread > current_spread + 4:
            token_manager.update_spread(token, spread)
            print('LIFE CHANGE')
            return {"Has_spread": True, "thread_id": None}
        elif spread < current_spread - 4:
            token_manager.update_spread(token, spread)
            print('LIFE CHANGE')
            return {"Has_spread": True, "thread_id": None}
        token_manager.update_spread(token, spread)
        return {"Has_spread": False, "thread_id": None}


# class SpreadIncreasedState(SpreadState):
#     def handle_spread(self, token: str, spread: float, minimum_spread: float, token_manager: TokenManager) -> bool:
#         current_spread = token_manager.get_current_spread(token)
#
#         if spread < minimum_spread:
#             token_manager.remove_spread(token)
#             return {"Has_spread": True, "thread_id": None}
#         elif spread < current_spread - 4:
#             token_manager.update_spread(token, spread)
#             return {"Has_spread": True, "thread_id": None}
#         return {"Has_spread": False, "thread_id": None}
#
#
# class SpreadDecreasedState(SpreadState):
#     def handle_spread(self, token: str, spread: float, minimum_spread: float, token_manager: TokenManager) -> bool:
#         if spread > minimum_spread:
#             token_manager.update_spread(token, spread)
#             return {"Has_spread": True, "thread_id": None}
#         return {"Has_spread": False, "thread_id": None}


if __name__ == '__main__':

    token_manager = TokenManager({"TEST": {}})
    spread_context = SpreadContext(token_manager)
    minimum_spread = 6

    # Симуляция изменения спреда
    spreads = [4, 10, 15, 10, 5]  # 5 - это меньше минимального, уведомления не должно быть
    spreads2 = [4, 10, 15, 10, 10, 11, 5]
    spreads3_with_life_change = [4, 10, 15, 10, 10, 11, 30, 35, 32, 32, 37, 5]

    for spread in spreads3_with_life_change:
        result = spread_context.handle_spread("TEST", spread, minimum_spread)
        logger.info(f"Spread: {spread}, Has_spread: {result['Has_spread']}")
        time.sleep(1)  # Имитируем задержку между проверками

    # spread: False, True, True, True, False
    # spread2: False, True, True, True, False, False, False
    # spread3: False, True, True, True, False, False, True, True, False, False, True, False
# false, true, ,true, trhe, falsem false, true, true, false, false, true, false
# ЗАМЕТКА: Все испытание прошло успешно. Все работает как ожидалось.
# Все тесты прошли успешно.
# Этот код старый, новый мы уже обновили в token_manager.py
# То что в закомментировано это старый код, в token_manager.py такой же самий как тут но без комментарий
