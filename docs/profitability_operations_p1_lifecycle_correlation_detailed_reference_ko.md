# Profitability / Operations P1 Lifecycle Correlation Detailed Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P1 lifecycle correlation observability`가 무엇인지, 왜 필요한지, 어떤 입력을 쓰고 어떤 출력을 만들어야 하는지 고정하기 위한 상세 기준 문서다.

핵심 질문은 이것이다.

`최근 손실이나 성능 저하가 entry 문제인지, wait 문제인지, exit 문제인지, 혹은 그 사이 handoff 문제인지 어떻게 한 번에 읽을 것인가?`

## 2. P1이 필요한 이유

현재 프로젝트는 이미 아래를 상당히 잘한다.

- entry 순간의 semantic 해석
- wait state와 soft/hard wait 구조화
- exit management와 stage/profile 분리
- forensic / coverage limitation 구분

하지만 지금 상태에선 여전히 해석이 쉽게 쪼개진다.

예를 들면 이런 식이다.

- entry row만 보고 `진입이 문제다`라고 생각한다
- closed trade만 보고 `exit가 너무 빠르다`고 생각한다
- wait가 실제로 손실을 줄였는지 아니면 기회를 죽였는지 읽기 어렵다

즉 지금 필요한 건 `점별 해석`이 아니라 `생애주기 해석`이다.

P1은 entry / wait / exit를 하나의 거래 lifecycle로 다시 묶어서 읽는 첫 상위 운영 단계다.

## 3. P1이 아닌 것

P1은 아래 작업과 다르다.

- 기대값 자체를 계산하는 일
- anomaly threshold를 설정하는 일
- 비교 리포트로 좋아짐/나빠짐을 결론내리는 일
- setup blacklist를 정하는 일

즉 P1은 `왜 그런 결과가 생겼는지 흐름을 읽는 단계`이고,
`얼마나 돈이 되는지`를 숫자로 정리하는 건 P2,
`어떻게 경보를 띄울지`는 P3,
`무엇을 바꿀지`는 P5에 더 가깝다.

## 4. P1의 핵심 해석 단위

P1은 아래 네 단위를 동시에 본다.

### 4-1. ticket lifecycle

한 ticket이

- 어떤 entry setup으로 열렸고
- 어떤 wait state를 거쳤고
- 어떤 exit family로 닫혔는지

를 본다.

### 4-2. decision lifecycle

entry decision row 단위로

- observe / blocked / wait / entered 비율
- blocked_by / action_none_reason / quick_trace_state
- 이후 실제 trade 결과

의 연결을 본다.

### 4-3. family lifecycle

아래 같은 family들이 실제 결과와 어떻게 이어지는지 본다.

- `consumer_stage`
- `entry_wait_state`
- `decision_winner`
- `decision_reason`
- `exit_wait_state`
- `blocked_by`

### 4-4. grouping lifecycle

이 lifecycle을 다시 아래 축으로 group해서 본다.

- symbol
- setup_id
- regime / market_mode
- action side
- coverage state

## 5. P1 입력 소스

현재 코드 기준 P1의 대표 입력은 아래다.

### entry side

- [entry_decisions.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
- [entry_decisions.detail.jsonl](C:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.detail.jsonl)

여기서 읽는 대표 필드:

- `setup_id`
- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `entry_wait_state`
- `entry_wait_reason`
- `consumer_check_stage`
- `consumer_guard_result`
- `p0_decision_owner_relation`
- `p0_coverage_state`
- `p0_decision_trace_v1`

### open / runtime side

- [trade_history.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\trade_history.csv)
- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py) 의 runtime diagnostics surface

여기서 읽는 대표 필드:

- `entry_setup_id`
- `entry_wait_state`
- `exit_profile`
- open position count / direction
- recent runtime diagnostics

### closed side

- [trade_closed_history.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\trade_closed_history.csv)

여기서 읽는 대표 필드:

- `decision_winner`
- `decision_reason`
- `exit_wait_state`
- `profit`
- `entry_setup_id`
- `open_time`
- `close_time`

## 6. 이미 있는 씨앗

P1은 완전히 0에서 시작하는 게 아니다.

이미 아래 씨앗이 있다.

- [lifecycle_watch_report.py](C:\Users\bhs33\Desktop\project\cfd\scripts\lifecycle_watch_report.py)
- [wait_engine.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\wait_engine.py)
- [exit_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_service.py)
- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [p0_decision_trace.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\p0_decision_trace.py)

중요한 해석은 이거다.

- `lifecycle_watch_report.py`는 좋은 seed지만 아직 운영 canonical surface는 아니다.
- P1은 이 seed를 `coverage-aware`, `setup/regime/symbol groupable`, `quick-read 가능한 latest report`로 승격시키는 단계다.

## 7. P1에서 반드시 지킬 규칙

1. `coverage_in_scope`와 `outside_coverage`를 섞지 않는다.
2. lifecycle correlation은 PnL 결론이 아니라 흐름 해석이 중심이다.
3. entry / wait / exit를 따로 최적화하지 말고 연결해서 본다.
4. consumer contract를 깨는 직접 semantic 재해석은 하지 않는다.
5. 운영자가 한 번에 읽을 수 있는 `latest json/csv/md` surface를 남긴다.

## 8. P1이 답해야 하는 질문

P1이 실제로 답할 수 있어야 하는 질문은 아래와 같다.

- 최근 손실은 entry timing이 약해서 생겼는가
- wait selected가 너무 많아 기회를 놓치는가
- exit family가 특정 setup에서 과도하게 빠른가
- blocked family가 실제로는 손실 회피로 작동하는가
- 어떤 symbol / setup / regime에서 lifecycle이 비정상적으로 꼬이는가

## 9. P1 산출물 형태

P1의 canonical 산출물은 아래 세 가지가 적절하다.

### 9-1. latest json

기계적으로 다시 읽을 수 있는 구조화 report.

예:

- overall lifecycle summary
- symbol summary
- setup summary
- regime summary
- coverage-aware split summary
- suspicious lifecycle clusters

### 9-2. latest csv

정렬 / 필터 / ad-hoc 분석이 쉬운 flat table.

예:

- symbol-setup-regime row
- blocked/wait/entered/closed count
- decision_winner / decision_reason ratios

### 9-3. latest md

운영자가 빠르게 읽는 quick memo.

예:

- “지금 손실은 entry보다 exit 쪽이 더 강함”
- “XAUUSD / range_upper_reversal_sell에서 wait->exit_now_support_bounce 연결이 몰림”

## 10. P1 완료 기준

P1이 완료됐다고 보려면 최소한 아래가 가능해야 한다.

1. entry / wait / exit 흐름을 한 표면에서 본다.
2. symbol / setup / regime 기준으로 lifecycle 이상 지점을 찾을 수 있다.
3. coverage-aware separation이 report에 들어간다.
4. operator가 quick memo만 읽고도 “지금 어디가 문제인지” 방향을 말할 수 있다.

## 11. 다음 단계와의 연결

P1이 닫히면 그 다음은 자연스럽게 P2로 간다.

관계는 아래처럼 보면 된다.

- `P1`: 왜 이런 결과가 생겼는가
- `P2`: 무엇이 실제로 돈이 되는가
- `P3`: 무엇이 비정상인가
- `P4`: 이전보다 좋아졌는가
- `P5`: 그래서 다음에 무엇을 바꿀 것인가

## 12. 한 줄 결론

P1은 `entry / wait / exit를 각각 보던 상태에서, 하나의 거래 생애주기로 다시 묶어 읽는 첫 운영 해석 단계`다. 현재 가장 자연스러운 시작점은 `P0 trace surface를 입력으로 쓰는 canonical lifecycle report`를 만드는 것이다.
