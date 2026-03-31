# symbol_resolver.py
"""
브로커마다 다른 심볼명을 자동 매핑하고,
시장 활성 여부(틱 신선도/스프레드)를 점검합니다.
"""

import time

import MetaTrader5 as mt5

from adapters.mt5_broker_adapter import MT5BrokerAdapter
from backend.core.config import Config
from ports.broker_port import BrokerPort


class SymbolResolver:
    """심볼 매핑 및 거래 가능 상태 확인."""

    def __init__(self, broker: BrokerPort | None = None):
        self.broker = broker or MT5BrokerAdapter()
        self.resolved = {}  # {"NAS100": "USTEC", ...}
        self.status = {}

    def find_symbols(self):
        """
        Config.SYMBOL_CANDIDATES 순서대로 실제 거래 가능한 심볼을 선택합니다.
        """
        all_symbols = self.broker.symbols_get()
        if not all_symbols:
            print("[ERROR] 심볼 목록을 가져올 수 없습니다.")
            return {}

        symbol_dict = {s.name: s for s in all_symbols}
        print("\n[INFO] 심볼 매핑 중...")

        for base_name, candidates in Config.SYMBOL_CANDIDATES.items():
            found = False
            for candidate in candidates:
                if candidate in symbol_dict:
                    info = symbol_dict[candidate]
                    # 거래 비활성 심볼은 제외
                    if info.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED:
                        self.resolved[base_name] = candidate
                        print(f"   [OK] {base_name} -> {candidate}")
                        found = True
                        break
            if not found:
                print(f"   [WARN] {base_name} -> 매핑 실패")

        return self.resolved

    def get_symbol(self, base_name):
        """기본 심볼명을 실제 브로커 심볼명으로 변환합니다."""
        return self.resolved.get(base_name, base_name)

    def check_market_active(self, symbol):
        """
        심볼의 현재 거래 가능 상태를 반환합니다.
        - 틱이 너무 오래되었는지
        - 스프레드가 제한을 초과하는지
        """
        tick = self.broker.symbol_info_tick(symbol)
        if not tick:
            return False, "틱 없음"

        tick_age = time.time() - tick.time
        if tick_age > 60:
            return False, f"휴장/지연 틱 ({int(tick_age)}초)"

        spread = tick.ask - tick.bid
        limit = Config.SPREAD_LIMITS.get("DEFAULT")
        for key in Config.SPREAD_LIMITS:
            if key in symbol.upper():
                limit = Config.SPREAD_LIMITS[key]
                break

        # 고가 자산은 절대 스프레드 제한을 비율 제한과 함께 사용
        if tick.bid > 10000:
            limit = max(limit, tick.bid * 0.001)  # 0.1%

        if spread > limit:
            return False, f"스프레드 과다 ({spread:.1f})"

        return True, "활성"

    def get_active_symbols(self):
        """매핑된 심볼 중 현재 활성 심볼만 반환합니다."""
        active = []
        for base_name, real_symbol in self.resolved.items():
            is_active, reason = self.check_market_active(real_symbol)
            self.status[base_name] = {
                "symbol": real_symbol,
                "active": is_active,
                "reason": reason,
            }
            if is_active:
                active.append(real_symbol)
        return active

    def print_status(self):
        """현재 심볼 상태를 콘솔에 출력합니다."""
        print("\n" + "=" * 50)
        print("[INFO] 시장 상태")
        print("=" * 50)

        for base_name, info in self.status.items():
            icon = "ACTIVE" if info["active"] else "INACTIVE"
            print(f"  {icon} {base_name:8} -> {info['symbol']:12} | {info['reason']}")

        print("=" * 50)
