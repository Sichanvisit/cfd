# State25 Log-Only vs Canary/Live Readiness Split

## 목적

이 문서는 `왜 readiness를 한 덩어리로 보지 않고 단계별로 나누는지`를 정리한다.

핵심은 이거다.

- `log_only`는 더 빨리 열 수 있다
- `canary/live`는 훨씬 더 늦게 열어야 한다

둘을 같은 문턱으로 묶어두면, 실제로는 harmless한 `log_only`까지 너무 안 열리게 된다.

## 왜 분리해야 하나

기존 해석은 사실상 이랬다.

- Step9 E5가 완전히 ready가 아니면
- AI4가 `hold_step9`
- AI5가 `disabled_hold`
- AI6도 `hold_disabled`

이 구조는 안전하지만, `seed shortfall`처럼 시간이 해결할 문제까지 전부 `log_only 금지`로 묶는다는 단점이 있었다.

즉 지금 필요한 건:

- `지금 당장 live를 열 수 있나?`
- `지금 당장 log_only 정도는 돌려도 되나?`

를 분리해서 보는 것이다.

## 이번에 나누는 두 종류의 조건

### 1. log_only readiness에 필요한 조건

이 단계는 `읽기/기록/비교` 위주다.

즉 틀려도 바로 주문 정책을 강하게 바꾸지 않는 단계라, 완전한 E5 readiness까지는 필요 없다.

이번에 `soft blocker`로 보는 것:

- `full_qa_seed_shortfall`
- `insufficient_primary_coverage`
- `insufficient_supported_pattern_classes`

이 세 개는 `데이터가 아직 덜 쌓임`에 가까운 문제라, log_only를 완전히 막을 이유로는 보지 않는다.

이번에 `hard blocker`로 남기는 것:

- `unresolved_high_confusions`
- `pilot_baseline_not_ready`
- `group_baseline_skipped`
- `pattern_baseline_skipped`
- `group_macro_f1_below_threshold`
- `pattern_macro_f1_below_threshold`

이쪽은 후보 자체가 아직 불안정하다는 뜻이라, log_only라도 열면 안 된다.

정리하면:

- 데이터가 부족해서 아직 덜 성숙한 상태는 `log_only 가능`
- 모델/분류가 아직 불안정한 상태는 `log_only 금지`

### 2. canary/live readiness에 필요한 조건

이 단계는 실제로 실행 정책에 영향이 갈 수 있는 단계다.

그래서 아래가 다 필요하다.

- Step9 execution handoff ready
- canary evidence 존재
- canary rows minimum 충족
- utility delta 이상 없음
- must_release / bad_exit / wait_drift / symbol_skew / watchlist_confusion 악화 없음

즉 `canary/live`는 여전히 기존처럼 빡세게 둔다.

## 새 해석

이번 분리 이후 흐름은 이렇게 읽는다.

1. `hold_offline`
2. `hold_step9`
3. `log_only_ready`
4. `promote_ready`
5. `rollback_recommended`

여기서 의미는 아래와 같다.

### `hold_step9`

critical blocker가 남아 있어서 아직 log_only도 열면 안 되는 상태다.

### `log_only_ready`

critical blocker는 없고, 남은 문제는 주로 seed/coverage 부족이다.

이때는:

- threshold/size는 log_only로 열 수 있다
- wait policy는 아직 별도 readiness를 본다
- canary/live는 아직 금지다

### `promote_ready`

full execution handoff도 ready고 canary evidence도 통과했다.

이때 비로소 bounded live 방향을 검토한다.

## 이번 코드 반영 의미

이번 변경으로:

- AI4는 `seed shortfall`만 있다고 무조건 `hold_step9`를 내리지 않는다
- AI5는 `log_only_ready`이면 threshold/size log_only를 열 수 있다
- AI6는 `log_only_ready + log_only_candidate_bind_ready + log_only` 조합이면 promote-log-only 후보로 본다

즉 전체 시스템이 더 빨리 움직이지만, 실제 live는 여전히 보수적으로 막아둔다.

## 핵심 한 줄

`데이터 부족은 log_only를 늦추는 이유일 뿐, 항상 금지하는 이유는 아니다. 반면 모델 불안정과 canary 악화는 여전히 canary/live까지 막아야 하는 hard gate다.`
