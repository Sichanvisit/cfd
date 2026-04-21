# Current Telegram Ops MVP Refinements

## 목적

이 문서는 [current_telegram_ops_mvp_templates_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_ops_mvp_templates_ko.md)를 기반으로, 추가 피드백 중 `MVP를 과하게 무겁게 만들지 않으면서도 운영 가치가 큰 항목`만 선별해 반영한 보완 규격이다.

`manage_cfd`와 텔레그램 승인 루프를 어떤 순서로 연결할지는 [current_telegram_control_plane_and_improvement_loop_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)를 함께 본다.

이번 문서에서 확정하는 핵심은 아래다.

1. 체크 카드는 `추천 행동`이 맨 위에 보이도록 재정렬한다.
2. `recommended_action`은 사람용 해석 문구를 함께 둔다.
3. `REDUCE`를 추천 행동 enum에 추가한다.
4. 청산 보고에는 `realized_r`를 넣는다.
5. 체크 카드에는 `trigger_summary`, `evidence_quality`, `scope_note`, `decision_deadline_ts`를 추가한다.
6. 버튼 이후 상태 전이를 체크 종류별로 최소 규격으로 고정한다.

---

## 이번 단계에서 반영하는 것

### Phase 1에 반영

- 체크 카드 순서 변경
- `recommended_action_note`
- `trigger_summary`
- `evidence_quality`
- `scope_note`
- `decision_deadline_ts`
- `REDUCE` enum 추가
- `report_exit.realized_r`
- `report_exit.initial_risk_usd`
- 버튼 의미 및 상태 전이 최소 규약
- `leg_id`, `checkpoint_id`, `checkpoint_type` 자리 확보

### Phase 2에 두는 것

- `risk_if_hold`
- `opportunity_if_exit`
- 동시 pending 상한 초과 시 묶음 요약 카드
- 전기간 대비 변화율
- `report_idle`

### 계속 보류

- 상시 LLM 요약
- 복잡한 조건부 승인 UI
- Sharpe 등 고급 지표
- scene full path 상세 카드

---

## 카드 재배치 원칙

기존보다 아래 순서를 우선한다.

1. 시스템 추천
2. 종목/방향/전략
3. 지금 알림이 뜬 이유
4. 핵심 리스크
5. 근거
6. 적용 범위와 만료

핵심 의도는 이거다.

- 카드를 열자마자 `무엇을 권하는지` 보일 것
- 왜 지금 내 판단이 필요한지 즉시 알 수 있을 것
- 누르면 무엇이 바뀌는지 감이 올 것

---

## 추가 필드

### 공통 envelope 확장

기존 envelope에 아래 필드를 추가한다.

- `recommended_action_note`
- `trigger_summary`
- `evidence_quality`
- `scope_note`
- `decision_deadline_ts`
- `leg_id`
- `checkpoint_id`
- `checkpoint_type`

예시:

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
  "trigger_summary": "최근 15분 동일 성격 요청 7건 누적",
  "recommended_action": "PROBE",
  "recommended_action_note": "소량 진입 허용 검토",
  "action_strength": "LOW",
  "evidence_quality": "MEDIUM",
  "scope_note": "이번 요청 1회 bounded 적용 검토",
  "decision_deadline_ts": "2026-04-11T00:00:00+09:00",
  "leg_id": "leg_btc_20260410_2125",
  "checkpoint_id": "chk_btc_20260410_2140_003",
  "checkpoint_type": "FIRST_PULLBACK_CHECK",
  "payload": {}
}
```

### 필드 의미

- `recommended_action_note`
  - 사람용 해석 한 줄
  - 예: `신규 진입 보류, 기존 포지션만 관리`
- `trigger_summary`
  - 왜 지금 카드가 떴는지
  - 예: `손실 확대 조건 충족`
- `evidence_quality`
  - 추천 강도와 별개인 근거 품질
  - `LOW`, `MEDIUM`, `HIGH`
- `scope_note`
  - 이번 승인/거부의 적용 범위
  - 예: `이번 요청 1회만 적용`
- `decision_deadline_ts`
  - 카드 유효 시한
  - 자정은 `24:00` 대신 다음 날 `00:00` ISO 시각으로 저장
- `leg_id`, `checkpoint_id`, `checkpoint_type`
  - PA 트랙 연결용 자리

---

## 체크 카드 최종 순서

### 템플릿 A2. 진입 체크 카드

```text
{priority_icon} {recommended_action} ({action_strength}) | ENTRY | {status}

{symbol} · {side} · {strategy_key}
scene: {scene_family}

왜 지금?
- {trigger_summary}

리스크
- {risk_line_1}
- {risk_line_2}

핵심 근거
- {reason_line_1}
- {reason_line_2}
- {reason_line_3}

시스템 해석
- {recommended_action_note}
- 근거 품질: {evidence_quality}

범위
- {scope_note}
- 누적: {pending_count}건

시간
- 최초: {first_event_ts}
- 최근: {last_event_ts}
- 만료: {decision_deadline_ts}
```

예시:

```text
🟡 PROBE (LOW) | ENTRY | PENDING

BTCUSD · BUY · strategy_a
scene: breakout_retest

왜 지금?
- 최근 15분 동일 성격 요청 7건 누적

리스크
- follow-through 약함
- 15분 내 실패 시 재하락 가능

핵심 근거
- lower rebound confirm
- bb20 reclaim
- short momentum recovery

시스템 해석
- 소량 진입 허용 검토
- 근거 품질: MEDIUM

범위
- 이번 요청 1회 bounded 적용 검토
- 누적: 7건

시간
- 최초: 2026-04-10 21:25 KST
- 최근: 2026-04-10 21:40 KST
- 만료: 2026-04-11 00:00 KST
```

---

## 초보자 운영 준비 메모

코드 구현 전에 텔레그램 안에서 아래만 먼저 준비해두면 된다.

1. 보고방 1개
2. 체크방 1개
3. PnL 포럼방 1개
4. PnL 토픽 `1H`, `4H`, `1D`, `1W`, `1M`
5. 봇을 세 방에 모두 추가
6. `chat_id`, `topic_id` 확보

자세한 절차는 [current_telegram_setup_quickstart_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_setup_quickstart_ko.md)를 따른다.

### 템플릿 B2. 청산 체크 카드

```text
{priority_icon} {recommended_action} ({action_strength}) | EXIT | {status}

{symbol} · {side} · {strategy_key}
scene: {scene_family}

왜 지금?
- {trigger_summary}

리스크
- 현재 손익: {current_pnl_text}
- 최대 유리: {mfe_text}
- 최대 불리: {mae_text}

핵심 근거
- {reason_line_1}
- {reason_line_2}
- {reason_line_3}

시스템 해석
- {recommended_action_note}
- 근거 품질: {evidence_quality}

범위
- {scope_note}
- 누적: {pending_count}건

시간
- 최초: {first_event_ts}
- 최근: {last_event_ts}
- 만료: {decision_deadline_ts}
```

예시:

```text
🟡 EXIT (MEDIUM) | EXIT | PENDING

XAUUSD · SHORT · strategy_b
scene: trend_exhaustion

왜 지금?
- 보유 edge 약화와 time decay 누적

리스크
- 현재 손익: -18.50 USD
- 최대 유리: +12.40 USD
- 최대 불리: -22.10 USD

핵심 근거
- follow-through failure
- time decay build-up
- structure quality weakening

시스템 해석
- 전량 청산 검토
- 근거 품질: MEDIUM

범위
- 현재 포지션 1건에만 적용
- 누적: 3건

시간
- 최초: 2026-04-10 22:05 KST
- 최근: 2026-04-10 22:11 KST
- 만료: 2026-04-10 22:20 KST
```

### 템플릿 C2. 리스크 체크 카드

```text
{priority_icon} {recommended_action} ({action_strength}) | RISK | {status}

{symbol}
상태: {risk_state_label}

왜 지금?
- {trigger_summary}

핵심
- {reason_line_1}
- {reason_line_2}

영향
- 신규 진입: {entry_effect}
- 기존 포지션: {position_effect}

시스템 해석
- {recommended_action_note}
- 근거 품질: {evidence_quality}

범위
- {scope_note}
- 만료: {decision_deadline_ts}
```

---

## 추천 행동 enum 보완

기존 enum에 `REDUCE`를 추가한다.

- `WAIT`
- `PROBE`
- `ENTER`
- `EXIT`
- `PARTIAL`
- `REDUCE`
- `HOLD`

의미는 아래처럼 구분한다.

- `PARTIAL`
  - 수익 확보 목적의 일부 청산
- `REDUCE`
  - 리스크 축소 목적의 일부 축소
- `EXIT`
  - 전량 종료

---

## action_strength 기준

`action_strength`는 아래 휴리스틱을 기본 규약으로 둔다.

### `LOW`

- 임계값 근처
- 근거 2개 이하
- scene 확정도가 낮음
- R/R이 애매함
- 해도 되고 안 해도 되는 수준

### `MEDIUM`

- 임계값 위
- 근거 3개 이상
- scene 신뢰도가 중간 이상
- R/R 1.5 이상
- 하는 쪽이 더 나은 수준

### `HIGH`

- 임계값을 크게 상회
- 핵심 근거 포함 4개 이상
- scene 확정도가 높음
- R/R 2.0 이상
- 또는 CRITICAL 리스크 상황
- 안 보면 손해인 수준

---

## evidence_quality 기준

`evidence_quality`는 추천 강도와 별도다.

### `LOW`

- 단편 근거만 있음
- 상위 timeframe 일치 약함
- 노이즈 가능성 큼

### `MEDIUM`

- 복수 근거가 서로 일치
- 큰 충돌 없음
- 아직 확정 직전은 아님

### `HIGH`

- 핵심 근거들이 같은 방향
- scene과 gate 정보가 일치
- 리스크와 기대가 모두 계산 가능

---

## 버튼 의미와 상태 전이

### 기본 원칙

- 버튼은 카드 종류마다 의미가 다를 수 있다.
- `승인`은 무조건 `approved` 저장만 하는 게 아니라, 카드 종류별 처리 규약을 따라야 한다.
- 버튼 결과는 `상태 저장`, `메시지 edit`, `callback ack`를 함께 수행한다.

### `check_entry + apply`

- `승인`
  - `approved`
  - 해당 group 1회 bounded apply 허용
  - 같은 key는 기존 병합 유지
- `거부`
  - `rejected`
  - 같은 key 15분 재상단 금지
- `보류`
  - `held`
  - 20분 후 재알림 후보

### `check_exit + apply`

- `승인`
  - `approved`
  - 즉시 exit signal 통과
- `거부`
  - `rejected`
  - 기존 포지션 유지
- `보류`
  - `held`
  - 5분 후 refresh 후보

### `check_risk + manage`

- `확인`
  - `approved`
  - 정보 확인 및 운영 경고 유지
- `긴급 조치`
  - `approved`
  - 사전에 정의된 비상 조치 실행
- `보류`
  - `held`
  - 재알림 후보

### 카드에 노출할 범위 문구 예시

- `이번 요청 1회 bounded 적용 검토`
- `현재 포지션 1건에만 적용`
- `기존 포지션만 영향, 신규 진입 차단`

---

## 보고방 보강

### `report_exit` 필드 확장

기존 `report_exit`에 아래 필드를 추가한다.

- `realized_r`
- `initial_risk_usd`
- `review_summary`

예시 payload:

```json
{
  "payload": {
    "entry_price": 83210.5,
    "exit_price": 83652.3,
    "realized_pnl": 44.2,
    "realized_r": 2.71,
    "initial_risk_usd": 16.3,
    "holding_time_text": "2h 15m",
    "reason_lines": [
      "target hit",
      "volume fade confirmed"
    ],
    "review_summary": "runner hold managed well"
  }
}
```

최종 보고 예시:

```text
💚 청산 | BTCUSD BUY | +44.20 USD (+2.71R)

진입: 83210.5
청산: 83652.3
보유: 2h 15m
scene: breakout_retest

청산 사유
- target hit
- volume fade confirmed

복기
- runner hold managed well
```

### `review_summary` 생성 규칙

초기에는 자유 텍스트보다 아래 규칙 기반 한 줄 생성을 권장한다.

1. MFE 대비 실현 비율이 낮으면
   - `MFE 대비 포착률 낮음`
2. gate가 발동 상태였으면
   - `진입 시 gate 영향 구간이었음`
3. 보유 시간이 길고 성과가 약하면
   - `time decay 누적으로 hold edge 약화`
4. 특이점이 없으면
   - 빈 값 허용

---

## 청산 체크의 조기 추가 후보

아래 둘은 Phase 2 후보로 미리 자리만 잡아둔다.

- `risk_if_hold`
- `opportunity_if_exit`

예시:

```json
{
  "payload": {
    "risk_if_hold": "-35.0 USD (스탑까지)",
    "opportunity_if_exit": "+12.0 USD (다음 저항까지)"
  }
}
```

---

## PnL 포럼 조기 확장 후보

초기 MVP엔 필수는 아니지만, 구조 자리는 잡아둘 만한 필드다.

- `prev_period_pnl`
- `pnl_change_pct`
- `prev_period_win_rate`
- `operating_tone`

`operating_tone` 예:

- `보수적`
- `공격적`
- `신규 진입 억제`

---

## 알림 가드 보완

기존 시간 기반 가드 외에 아래를 Phase 2 후보로 둔다.

- `TELEGRAM_CHECK_MAX_CONCURRENT_PENDING`
- `TELEGRAM_CHECK_BATCH_SUMMARY_ENABLED`

의미:

- 동시 pending이 너무 많으면 개별 카드 난사 대신 묶음 요약 카드 우선

---

## 구현 순서 조정안

이번 보완을 반영한 추천 순서는 아래다.

1. `TelegramCheckCardFormatter`
2. `TelegramReportFormatter`
3. 이벤트 envelope 고정
4. `check_entry`, `check_exit`
5. 버튼 의미와 상태 전이 규약 구현
6. 병합 키에 `scene_family`, `direction_bias` 반영
7. `report_exit.realized_r` 적용
8. `1D` PnL 카드
9. 이후 `1H`, `4H`, `1W`, `1M` 확장

---

## 최종 기준

이번 보완 이후 MVP가 지켜야 할 핵심은 아래다.

1. 추천 행동이 카드 최상단에 보일 것
2. 카드에는 `왜 지금`, `무엇을 권하는지`, `누르면 무엇이 바뀌는지`가 들어갈 것
3. `action_strength`와 `evidence_quality`를 분리할 것
4. `REDUCE`와 `realized_r`를 초기에 반영할 것
5. 버튼은 단순 UI가 아니라 상태 전이 규약과 함께 설계할 것
