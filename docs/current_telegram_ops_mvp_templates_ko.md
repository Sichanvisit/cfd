# Current Telegram Ops MVP Templates And Event Schema

## 목적

이 문서는 텔레그램 운영 레이어 설계 중에서 바로 구현 가치가 높은 부분만 추려서 정리한 `MVP 기준서`다.

대상 범위는 아래 3개다.

1. 실제로 보낼 체크 카드 템플릿
2. 허브에서 사용할 이벤트 스키마
3. 지금 먼저 반영할 필드 목록

이 문서는 기존 허브 설계 문서인 [current_telegram_notification_hub_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_notification_hub_design_ko.md)의 후속 세부 규격으로 본다.

`manage_cfd -> approval -> improvement loop` 전체 연결 방향은 [current_telegram_control_plane_and_improvement_loop_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)를 따른다.

추가 피드백을 선별 반영한 보완 규격은 [current_telegram_ops_mvp_refinements_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_ops_mvp_refinements_ko.md)를 따른다.

텔레그램 방 생성, bot 권한, `chat_id`/`topic_id` 확보 절차는 [current_telegram_setup_quickstart_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_setup_quickstart_ko.md)를 따른다.

---

## 지금 채택할 핵심

이번 단계에서는 아래만 먼저 반영한다.

1. 체크방 메시지를 `결정 카드` 중심으로 바꾼다.
2. `recommended_action`와 `action_strength`를 추가한다.
3. 체크 병합 키에 `scene_family`와 `direction_bias`를 넣는다.
4. 보고방 메시지는 `왜 진입/청산했는가` 중심으로 줄인다.
5. PnL 포럼에는 `drawdown`을 넣는다.
6. 메시지 길이와 알림 빈도 가드를 넣는다.

이번 단계에서 보류한다.

1. 상시 LLM 요약
2. 과도한 이벤트 타입 세분화
3. 지나치게 복잡한 버튼 종류
4. Sharpe 같은 고급 지표

---

## 공통 원칙

### 1. 정보형이 아니라 판단형

메시지는 아래 순서로 보이게 한다.

1. 지금 무엇을 보고 있는지
2. 왜 판단이 필요한지
3. 가장 큰 리스크가 무엇인지
4. 시스템 추천이 무엇인지
5. 내가 누를 버튼이 무엇인지

### 2. 시스템 추천과 운영자 액션 분리

아래 둘은 다르다.

- 시스템 추천: `WAIT`, `PROBE`, `ENTER`, `EXIT`, `PARTIAL`
- 운영자 액션: `승인`, `거부`, `보류`

### 3. 점수는 내부용, 카드는 해석용

`score`는 저장은 하되 카드 본문 전면에는 두지 않는다.

카드에는 아래를 우선 노출한다.

- 핵심 근거
- 리스크
- 추천 행동
- 강도

### 4. 길이 제한

초기 제한값은 아래로 둔다.

- 체크 카드: 800자 이내
- 진입/청산 보고: 700자 이내
- PnL `1H`, `4H`: 300자 이내
- PnL `1D`, `1W`, `1M`: 1800자 이내

---

## 체크 카드 템플릿

체크 카드의 최신 카드 순서와 추가 필드는 [current_telegram_ops_mvp_refinements_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_ops_mvp_refinements_ko.md)를 canonical source로 본다.

이 문서의 템플릿은 `기본 envelope / payload shape`에 집중하고, 구현 직전 필드 우선순위는 refinements 문서를 우선한다.

### 공통 필드

체크 카드에는 아래 필드를 공통으로 사용한다.

- `priority_icon`
- `check_kind_label`
- `status`
- `symbol`
- `side`
- `strategy_key`
- `scene_family`
- `pending_count`
- `reason_summary`
- `risk_summary`
- `recommended_action`
- `action_strength`
- `first_event_ts`
- `last_event_ts`

### 우선순위 아이콘

- `CRITICAL` -> `🔴`
- `HIGH` -> `🟡`
- `NORMAL` -> `🔵`
- `LOW` -> `⚪`

---

### 템플릿 A. 진입 체크 카드

```text
{priority_icon} 체크 요청 | ENTRY | {status}

종목: {symbol}
방향: {side}
전략: {strategy_key}
scene: {scene_family}
누적: {pending_count}건

판단 요약
- {reason_line_1}
- {reason_line_2}
- {reason_line_3}

리스크
- {risk_line_1}
- {risk_line_2}

시스템 추천
- {recommended_action} ({action_strength})

시간
- 최초: {first_event_ts}
- 최근: {last_event_ts}
```

권장 버튼:

- `승인`
- `거부`
- `보류`
- `상세`

예시:

```text
🟡 체크 요청 | ENTRY | PENDING

종목: BTCUSD
방향: BUY
전략: strategy_a
scene: breakout_retest
누적: 7건

판단 요약
- lower rebound confirm
- bb20 reclaim
- short momentum recovery

리스크
- follow-through 약함
- 15분 내 실패 시 재하락 가능

시스템 추천
- PROBE (LOW)

시간
- 최초: 2026-04-10 21:25 KST
- 최근: 2026-04-10 21:40 KST
```

---

### 템플릿 B. 청산 체크 카드

```text
{priority_icon} 체크 요청 | EXIT | {status}

종목: {symbol}
방향: {side}
전략: {strategy_key}
scene: {scene_family}
누적: {pending_count}건

현재 상황
- 현재 손익: {current_pnl_text}
- 최대 유리: {mfe_text}
- 최대 불리: {mae_text}

청산 근거
- {reason_line_1}
- {reason_line_2}
- {reason_line_3}

시스템 추천
- {recommended_action} ({action_strength})

시간
- 최초: {first_event_ts}
- 최근: {last_event_ts}
```

권장 버튼:

- `전량 청산`
- `거부`
- `보류`
- `상세`

예시:

```text
🟡 체크 요청 | EXIT | PENDING

종목: XAUUSD
방향: SHORT
전략: strategy_b
scene: trend_exhaustion
누적: 3건

현재 상황
- 현재 손익: -18.50 USD
- 최대 유리: +12.40 USD
- 최대 불리: -22.10 USD

청산 근거
- follow-through 실패
- time decay 누적
- 구조 보존 약화

시스템 추천
- EXIT (MEDIUM)

시간
- 최초: 2026-04-10 22:05 KST
- 최근: 2026-04-10 22:11 KST
```

---

### 템플릿 C. 리스크 체크 카드

```text
{priority_icon} 체크 요청 | RISK | {status}

종목: {symbol}
상태: {risk_state_label}

핵심
- {reason_line_1}
- {reason_line_2}

영향
- 신규 진입: {entry_effect}
- 기존 포지션: {position_effect}

시스템 추천
- {recommended_action} ({action_strength})
```

권장 버튼:

- `확인`
- `긴급 조치`
- `보류`

예시:

```text
🔴 체크 요청 | RISK | PENDING

종목: BTCUSD
상태: spread spike

핵심
- spread 0.5pt -> 3.2pt 급등
- 신규 진입 품질 급락

영향
- 신규 진입: 차단 권장
- 기존 포지션: 정상 관리

시스템 추천
- WAIT (HIGH)
```

---

## 보고방 최소 템플릿

### 템플릿 D. 진입 보고

```text
🟢 진입 | {symbol} {side}

진입가: {entry_price}
수량: {size_text}
전략: {strategy_key}
scene: {scene_family}

진입 근거
- {reason_line_1}
- {reason_line_2}

리스크 메모
- {risk_line_1}
```

### 템플릿 E. 청산 보고

```text
{exit_icon} 청산 | {symbol} {side} | {realized_pnl_text}

진입: {entry_price}
청산: {exit_price}
보유: {holding_time_text}
scene: {scene_family}

청산 사유
- {reason_line_1}
- {reason_line_2}

복기 포인트
- {review_line_1}
```

원칙:

- 보고방은 `무슨 일이 있었는가`보다 `왜 그렇게 했는가`를 보여준다.
- 수익/손실 숫자만 늘어놓는 메시지는 만들지 않는다.

---

## PnL 포럼 최소 템플릿

### 템플릿 F. 1H / 4H 요약

```text
📊 {window_label}

실현 손익: {realized_pnl_text}
거래: {trade_count}건
승률: {win_rate_text}
최대 낙폭: {drawdown_text}
```

### 템플릿 G. 1D / 1W / 1M 요약

```text
📊 {window_label}

실현 손익: {realized_pnl_text}
미실현: {open_pnl_text}

성과
- 거래: {trade_count}건
- 승률: {win_rate_text}
- 최대 낙폭: {drawdown_text}
- 최고 거래: {best_trade_text}
- 최악 거래: {worst_trade_text}

주요 진입 근거
- {top_entry_reason_1}
- {top_entry_reason_2}

주요 청산 근거
- {top_exit_reason_1}
- {top_exit_reason_2}
```

---

## 이벤트 스키마

### 공통 envelope

모든 이벤트는 아래 공통 envelope를 가진다.

```json
{
  "event_id": "evt_20260410_214025_btc_entry_001",
  "event_type": "check_entry",
  "route_key": "check",
  "created_at": "2026-04-10T21:40:25+09:00",
  "priority": "HIGH",
  "symbol": "BTCUSD",
  "side": "BUY",
  "strategy_key": "strategy_a",
  "scene_family": "breakout_retest",
  "direction_bias": "continuation_up",
  "reason_codes": [
    "lower_rebound_confirm",
    "bb20_reclaim",
    "momentum_recovery"
  ],
  "reason_summary": "Lower rebound confirm with BB20 reclaim and short momentum recovery.",
  "risk_summary": "Follow-through is still weak and can fail within the next 15 minutes.",
  "recommended_action": "PROBE",
  "action_strength": "LOW",
  "payload": {}
}
```

필수 필드:

- `event_id`
- `event_type`
- `route_key`
- `created_at`
- `priority`
- `symbol`
- `reason_summary`
- `recommended_action`
- `action_strength`

강력 권장 필드:

- `side`
- `strategy_key`
- `scene_family`
- `direction_bias`
- `reason_codes`
- `risk_summary`

### `event_type` 초기 범위

초기에는 아래만 쓴다.

- `check_entry`
- `check_exit`
- `check_risk`
- `report_entry`
- `report_exit`
- `pnl_update`
- `pnl_close`

---

## 체크 이벤트 payload

### A. `check_entry`

```json
{
  "payload": {
    "entry_price": 83210.5,
    "target_price": 84500.0,
    "stop_price": 82800.0,
    "position_size_hint": "0.05 lot",
    "pending_count": 7,
    "first_event_ts": "2026-04-10T21:25:00+09:00",
    "last_event_ts": "2026-04-10T21:40:00+09:00",
    "reason_lines": [
      "lower rebound confirm",
      "bb20 reclaim",
      "short momentum recovery"
    ],
    "risk_lines": [
      "follow-through weak",
      "failure possible within 15 minutes"
    ]
  }
}
```

### B. `check_exit`

```json
{
  "payload": {
    "entry_price": 3187.24,
    "current_price": 3189.09,
    "current_pnl": -18.5,
    "mfe": 12.4,
    "mae": -22.1,
    "pending_count": 3,
    "first_event_ts": "2026-04-10T22:05:00+09:00",
    "last_event_ts": "2026-04-10T22:11:00+09:00",
    "reason_lines": [
      "follow-through failure",
      "time decay build-up",
      "structure quality weakening"
    ]
  }
}
```

### C. `check_risk`

```json
{
  "payload": {
    "risk_state_label": "spread spike",
    "entry_effect": "block_new_entries",
    "position_effect": "manage_only",
    "reason_lines": [
      "spread expanded from 0.5pt to 3.2pt",
      "execution quality degraded sharply"
    ]
  }
}
```

---

## 보고 이벤트 payload

### D. `report_entry`

```json
{
  "payload": {
    "entry_price": 83210.5,
    "size_text": "0.05 lot",
    "reason_lines": [
      "bb20 reclaim",
      "lower rebound confirm"
    ],
    "risk_lines": [
      "follow-through still weak"
    ]
  }
}
```

### E. `report_exit`

```json
{
  "payload": {
    "entry_price": 83210.5,
    "exit_price": 83652.3,
    "realized_pnl": 44.2,
    "holding_time_text": "2h 15m",
    "reason_lines": [
      "target hit",
      "volume fade confirmed"
    ],
    "review_lines": [
      "runner hold managed well"
    ]
  }
}
```

---

## PnL 이벤트 payload

### F. `pnl_update`

```json
{
  "payload": {
    "window_code": "1D",
    "window_label": "2026-04-10 일간",
    "realized_pnl": 132.4,
    "open_pnl": -8.1,
    "trade_count": 11,
    "win_rate": 0.636,
    "drawdown": -18.2,
    "best_trade_pnl": 44.2,
    "worst_trade_pnl": -18.5,
    "top_entry_reasons": [
      "lower_rebound_confirm",
      "bb20_reclaim"
    ],
    "top_exit_reasons": [
      "target_hit",
      "adverse_exit"
    ]
  }
}
```

### G. `pnl_close`

`pnl_update`와 같은 payload를 쓰되, 메시지는 `편집되지 않는 확정 메시지`로 보낸다.

---

## 체크 병합 키

초기 병합 키는 아래로 고정한다.

```text
{symbol}|{side}|{strategy_key}|{check_kind}|{action_target}|{scene_family}|{direction_bias}|{time_bucket}
```

예:

```text
BTCUSD|BUY|strategy_a|entry_review|apply|breakout_retest|continuation_up|2026-04-10T21:30+09:00/15m
```

이번에 새로 꼭 넣는 필드는 아래 2개다.

- `scene_family`
- `direction_bias`

---

## 우선 반영 필드 목록

### Phase 1. 지금 바로 구현할 필드

- `event_id`
- `event_type`
- `route_key`
- `created_at`
- `priority`
- `symbol`
- `side`
- `strategy_key`
- `scene_family`
- `direction_bias`
- `reason_codes`
- `reason_summary`
- `risk_summary`
- `recommended_action`
- `recommended_action_note`
- `action_strength`
- `trigger_summary`
- `evidence_quality`
- `scope_note`
- `decision_deadline_ts`
- `leg_id`
- `checkpoint_id`
- `checkpoint_type`

check entry/exit payload에서 바로 쓸 필드:

- `pending_count`
- `first_event_ts`
- `last_event_ts`
- `reason_lines`
- `risk_lines`
- `entry_price`
- `target_price`
- `stop_price`
- `current_price`
- `current_pnl`
- `mfe`
- `mae`

PnL에서 바로 쓸 필드:

- `window_code`
- `window_label`
- `realized_pnl`
- `open_pnl`
- `trade_count`
- `win_rate`
- `drawdown`
- `best_trade_pnl`
- `worst_trade_pnl`
- `top_entry_reasons`
- `top_exit_reasons`

### Phase 2. 다음에 붙일 필드

- `review_summary`
- `gate_name`
- `gate_effect`
- `position_size_hint`
- `holding_time_text`
- `condition_label`
- `operator_note`

### 보류 필드

- `llm_summary`
- `sharpe`
- `profit_factor` 고급 분해
- `mfe_capture_ratio`
- `scene_path_full`
- `market_regime_detail`

이 항목들은 나중에 붙여도 운영 MVP 가치는 충분하다.

---

## 추천 enum

### `recommended_action`

- `WAIT`
- `PROBE`
- `ENTER`
- `EXIT`
- `PARTIAL`
- `REDUCE`
- `HOLD`

### `action_strength`

- `LOW`
- `MEDIUM`
- `HIGH`

### `priority`

- `CRITICAL`
- `HIGH`
- `NORMAL`
- `LOW`

### `route_key`

- `check`
- `report`
- `pnl`

---

## 알림 가드

초기 규칙은 아래로 둔다.

- 같은 체크 그룹은 15분 내 새 메시지 재발송 금지
- 같은 체크 그룹은 edit 우선
- `CRITICAL`만 5분 재알림 허용
- 보고방은 진입/청산만 즉시
- PnL `1H`는 정시, `4H`는 4시간 단위, `1D`는 30분 edit

---

## 구현 순서

### 1. 포맷터부터 만든다

먼저 포맷터를 만들고 문자열 길이 검증을 넣는다.

권장 클래스:

- `TelegramCheckCardFormatter`
- `TelegramReportFormatter`
- `TelegramPnlFormatter`

### 2. 이벤트 envelope를 고정한다

허브에 문자열을 넘기지 말고 envelope dict를 넘긴다.

### 3. 체크 이벤트 두 종류만 먼저 붙인다

- `check_entry`
- `check_exit`

### 4. 보고 이벤트 두 종류를 붙인다

- `report_entry`
- `report_exit`

### 5. PnL은 `1D`부터 붙인다

그 다음 `1H`, `4H`, `1W`, `1M`으로 확장한다.

---

## 최종 기준

이번 MVP에서 가장 중요한 것은 아래다.

1. 카드가 `읽는 메시지`가 아니라 `판단하는 메시지`일 것
2. 시스템 추천과 운영자 버튼을 분리할 것
3. 이벤트 스키마는 넓게 벌리지 말고 공통 필드를 먼저 고정할 것
4. 병합은 시간뿐 아니라 `scene_family`와 `direction_bias`를 반영할 것
5. PnL에는 반드시 `drawdown`을 포함할 것
