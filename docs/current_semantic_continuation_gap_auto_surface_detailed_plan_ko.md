# Semantic Continuation Gap Auto Surface

## 목적

사용자가 따로 `/detect_feedback`로 설명하지 않아도, `계속 올라갈 수 있는 장면이 semantic observe/blocked로만 흘러가는 경우`를 자동 관찰 후보로 surface한다.

## 왜 이 보강이 필요한가

- 기존 `semantic baseline no-action cluster`는 전체 baseline count 기준 share를 사용해서 BTC 군집이 큰 날 NAS100/XAUUSD 개별 군집이 묻히는 문제가 있었다.
- 특히 `NAS100 | upper_break_fail_confirm | energy_soft_block | execution_soft_blocked`는 심볼 내부 비중이 높아도 global share가 낮으면 detector/propose에서 잘 안 보였다.
- 사용자는 이를 `계속 올라갈 것 같은데 전달/표식이 충분히 안 되는 문제`로 체감했다.

## 이번 slice에서 한 일

1. `symbol-local share`를 같이 계산한다.
   - `cluster_share`: 전체 baseline_no_action 대비 비중
   - `cluster_symbol_share`: 해당 심볼 baseline_no_action 대비 비중
2. cluster qualify를 `global share OR symbol-local share` 기준으로 연다.
3. `upper_break_fail_confirm`, `upper_reclaim_strength_confirm` 계열은 generic cluster가 아니라
   - `상승 지속 누락 가능성 관찰`
   로 별도 해석한다.
4. registry key도 별도 부여한다.
   - `misread:semantic_continuation_gap_cluster`

## 기대 결과

- `/detect`에서 NAS100 continuation-like blocked scene이 더 직접적인 한국어로 surface된다.
- `/propose`에서 semantic observe cluster 후보가 BTC 편중만 보이지 않고, NAS100 continuation gap도 review 후보로 같이 보인다.
- 사용자가 별도 설명을 붙이지 않아도 `자동 관찰 -> detector/propose 누적`이 먼저 된다.

## 이번 단계에서 의도적으로 하지 않은 것

- semantic threshold 자동 완화
- live action 자동 승격
- forecast를 메인 방향 결정권으로 승격

이번 단계는 어디까지나 `자동 관찰 언어와 candidate surface`를 보강하는 slice다.
