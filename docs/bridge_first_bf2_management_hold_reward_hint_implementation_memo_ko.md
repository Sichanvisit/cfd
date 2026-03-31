# BF2 Management Hold Reward Hint Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 목적

이 메모는 `BF2 management_hold_reward_hint_v1`의 첫 구현 패스를 코드/테스트 기준으로 닫기 위한 기록이다.

이번 패스의 목표는 아래 두 가지였다.

- management forecast가 hold reward 장면을 더 잘 설명하도록 만든다.
- `continue / recover / reach` 쪽 positive hold hint를 작은 bridge로 분리한다.

## 2. 이번에 구현한 것

### 2-1. feature metadata에 BF2 bridge 추가

아래 파일에 BF2 summary를 추가했다.

- [forecast_features.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_features.py)

새 summary shape:

- `management_hold_reward_hint_v1`
  - `hold_reward_hint`
  - `edge_to_edge_tailwind`
  - `hold_patience_allowed`
  - `component_scores`
  - `reason_summary`

입력은 기존 semantic 입력만 사용했다.

- `State`
- `Evidence`
- `Belief`
- `Barrier`

### 2-2. trade management forecast에 BF2 blend 추가

아래 파일에 BF2 helper와 management blend를 추가했다.

- [forecast_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_engine.py)

이번 패스에서 한 일:

1. feature metadata에서 BF2 summary를 읽는 helper 추가
2. 아래 관리 지표에 soft blend
   - `p_continue_favor`
   - `p_fail_now`
   - `p_recover_after_pullback`
   - `p_reach_tp1`
   - `p_opposite_edge_reach`
3. metadata에 `bridge_first_v1.management_hold_reward_hint_v1` 추가
4. component_scores에 BF2 trace 추가
5. forecast_reasons에 BF2 reason trace 추가

즉 이제 management forecast는

- base hold/cut math
- scene management support
- BF2 hold reward bridge

를 같이 설명할 수 있다.

## 3. 이번 패스에서 잠근 계약

### 3-1. BF2는 positive hold bridge다

BF2는 hold reward 양수 힌트를 먼저 다루는 단계다.

- `hold_reward_hint`
- `edge_to_edge_tailwind`
- `hold_patience_allowed`

즉 fast cut risk는 이번 패스에서 주역이 아니다.

### 3-2. BF2도 owner가 아니다

scene / management base math가 owner고,
BF2는 modifier다.

즉 BF2가 장면을 새로 만들진 않는다.

### 3-3. additive first-pass를 유지한다

이번 패스도 기존 management forecast를 뒤집지 않았다.
scene support 뒤에 soft blend만 얹었다.

## 4. 테스트

이번 BF2에서 새로 잠근 테스트는 아래와 같다.

- [test_forecast_contract.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_forecast_contract.py)
  - feature metadata에 BF2 summary가 노출되는지
  - management forecast metadata/reason trace에 BF2가 남는지
  - BF2 bridge가 continue/reach 쪽을 실제로 boost 하는지

실행 결과:

- targeted: `37 passed`
- full unit: `1181 passed, 127 warnings`

## 5. 이번 구현의 해석

이번 BF2로 확인한 건 아래다.

1. hold reward를 작은 bridge로 분리할 수 있다.
2. 이 bridge는 management forecast에 바로 연결 가능하다.
3. raw를 더 늘리지 않아도 hold 쪽 설명력을 조금 더 끌어올릴 수 있다.

## 6. 아직 안 한 것

- `BF3 management_fast_cut_risk_v1`
- hold/exit product acceptance 직접 연결
- activation/reliability bridge

즉 이번 BF2는 `positive hold hint`만 먼저 연 first-pass다.

## 7. 다음 액션

가장 자연스러운 다음 순서는 아래다.

1. full unit 회귀 확인
2. BF2 close-out 유지
3. `BF3 management_fast_cut_risk_v1`로 이동

## 8. 한 줄 요약

```text
BF2는 hold reward 장면을 hold_reward_hint / edge_to_edge_tailwind / hold_patience_allowed로 요약해, trade management forecast의 continue/reach 쪽 설명력을 높인 first-pass bridge 구현이다.
```
