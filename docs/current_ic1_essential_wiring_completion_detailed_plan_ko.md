# IC1 Essential Wiring Completion 상세 계획

## 목적

이번 단계의 목적은 새 규칙을 더 붙이는 것이 아니라, 이미 만든 판단이 실제 runtime row, chart, flow history, execution trace에 같은 의미로 남도록 필수 배선을 완결하는 것이다.

핵심 범위:

- `current-cycle continuation overlay -> execution`
- `chart/flow history -> 최신 판단 동기화`
- `execution_diff_*` live 축적
- `continuation_accuracy_*` live 축적
- `심볼 공용 의미 계약` surface 정리

상위 기준 문서:

- [current_master_implementation_roadmap_navigation_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_master_implementation_roadmap_navigation_ko.md)
- [current_remaining_integration_completion_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_remaining_integration_completion_execution_roadmap_ko.md)
- [current_ca2_guard_promotion_bounded_live_validation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_ca2_guard_promotion_bounded_live_validation_execution_roadmap_ko.md)

## 현재 판단

많은 배선은 이미 닫혔다. 다만 live 검증 전에 마지막으로 보강해야 하는 부분이 남아 있었다.

남은 핵심:

1. single-row current-cycle enrich가 `execution_diff`와 `accuracy` flat field를 바로 surface하는가
2. runtime status detail에 wiring audit가 같이 남는가
3. chart/flow history가 최신 overlay event와 같은 방향 가족으로 동기화되는가
4. execution trace가 nested payload만 있을 때도 flat surface를 잃지 않는가

## 구현 원칙

### 1. single-row와 batch-row는 같은 계약을 쓴다

- `build_entry_runtime_signal_row(...)`
- `build_chart_painter_runtime_row(...)`
- `latest_signal_by_symbol`

이 세 경로가 같은 enrich helper를 통해

- `directional_continuation_overlay_*`
- `directional_continuation_accuracy_*`
- `execution_diff_*`

를 같은 이름으로 surface해야 한다.

### 2. nested contract와 flat surface를 같이 유지한다

실행층의 truth source는 여전히 nested payload다.

- `execution_action_diff_v1`

하지만 운영과 디버깅은 flat field가 빠르다.

- `execution_diff_original_action_side`
- `execution_diff_guarded_action_side`
- `execution_diff_promoted_action_side`
- `execution_diff_final_action_side`

그래서 nested를 유지하면서 missing flat field를 보정하는 방향으로 간다.

### 3. wiring 상태도 artifact로 남긴다

단순히 row를 눈으로 보는 대신, wiring이 실제 살아 있는지 요약 artifact를 만든다.

- `runtime_signal_wiring_audit_latest.json`
- `runtime_signal_wiring_audit_latest.md`

## 세부 작업

### A. execution/current-cycle surface 보강

대상:

- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

작업:

- single-row enrich 종료 시점에 `execution_diff` flat field normalize
- single-row enrich 종료 시점에 current accuracy flat field attach
- `ai_entry_traces` append 경로에서도 nested diff만 있어도 flat field가 남도록 정규화

완료 조건:

- entry/chart row에서 nested만 있어도 `execution_diff_*`가 바로 보임
- accuracy report가 있으면 row에 `directional_continuation_accuracy_*`가 붙음

### B. runtime signal wiring audit 추가

대상:

- [runtime_signal_wiring_audit.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\runtime_signal_wiring_audit.py)
- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

작업:

- `latest_signal_by_symbol`, `ai_entry_traces`, `accuracy_report`, `flow history`를 기준으로
  - overlay present
  - execution diff surface
  - accuracy surface
  - flow sync
  요약
- runtime status detail payload에 audit summary/artifact path export

완료 조건:

- runtime detail에서 wiring audit summary를 바로 볼 수 있음
- shadow auto에 JSON/MD artifact가 남음

### C. live 확인 포인트 고정

필드:

- `directional_continuation_overlay_event_kind_hint`
- `directional_continuation_accuracy_correct_rate`
- `execution_diff_original_action_side`
- `execution_diff_final_action_side`
- `runtime_signal_wiring_audit_summary_v1`

파일:

- [runtime_status.detail.json](C:\Users\bhs33\Desktop\project\cfd\data\runtime_status.detail.json)
- [NAS100_flow_history.json](C:\Users\bhs33\AppData\Roaming\MetaQuotes\Terminal\Common\Files\NAS100_flow_history.json)
- [XAUUSD_flow_history.json](C:\Users\bhs33\AppData\Roaming\MetaQuotes\Terminal\Common\Files\XAUUSD_flow_history.json)
- [BTCUSD_flow_history.json](C:\Users\bhs33\AppData\Roaming\MetaQuotes\Terminal\Common\Files\BTCUSD_flow_history.json)

## 검증 전략

### 단위 테스트

- single-row enrich가 accuracy/diff field를 붙이는지
- runtime status가 audit summary/artifact path를 싣는지
- audit service가 per-symbol summary와 flow sync를 계산하는지

### live 관찰

짧게 본다:

1. 같은 구조면 같은 방향 가족으로 찍히는지
2. `WAIT`만 남지 않고 `BUY_WATCH/SELL_WATCH`가 실제로 남는지
3. execution diff가 `original -> final`을 남기는지

## 다음 단계 연결

IC1이 닫히면 다음은 CA2/BC11로 간다.

1. CA2 KPI 누적
2. `weight bounded live` canary
3. `threshold bounded live`
4. `size`는 마지막
