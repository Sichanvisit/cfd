# Product Acceptance Reorientation Detailed Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 현재 프로젝트의 우선순위를
`운영 해석 / guarded overlay 검증`
중심에서
`제품 acceptance`
중심으로 다시 정렬하기 위한 상세 기준 문서다.

핵심 질문은 아래다.

`어떤 owner와 어떤 파일을 어떻게 건드려야, 내가 원하는 방향으로 차트 체크 표기, 자동 진입, 기다림/홀드, 청산이 실제로 체감되게 맞춰질 것인가?`

이 문서의 목적은 새 foundation을 만드는 것이 아니다.
이미 구축된 구조 위에서
`내가 마음에 드는 제품 동작`
을 다시 메인 기준으로 세우는 것이다.

## 2. 왜 방향을 다시 잡아야 하나

지금까지 많은 것이 구축되었다.

- semantic foundation
- consumer-coupled check / entry 구조
- entry / wait / exit 계약
- runtime summary / continuity / casebook
- profitability / operations surface
- guarded proposal / size overlay 실험 표면

하지만 사용자 체감 기준의 핵심 질문은 아직 남아 있다.

- 차트에 찍히는 체크가 정말 내가 보고 싶은 방식인가
- 자동으로 들어가는 자리가 정말 내가 동의하는 자리인가
- 기다림/홀드가 너무 조급하거나 너무 둔하지는 않은가
- 청산이 너무 빨리 끊거나 너무 늦게 놓지는 않는가

즉 지금 상태는
`구조 구축은 많이 끝났지만 제품 체감 acceptance는 아직 닫히지 않은 상태`
에 가깝다.

그래서 지금은 새 기능을 더 얹는 것보다
`제품 acceptance를 다시 메인축으로 놓는 것`
이 맞다.

## 3. 이 문서가 전제하는 현재 상태

아래는 이미 있는 것으로 본다.

- painter가 의미 owner가 아니라는 원칙
- consumer_check_state_v1 기반 chart/check/entry 연결
- late guard reconciliation 구조
- wait / exit의 contract와 runtime surface
- P1~P7 profitability/operations surface

즉 이 문서는 “아무것도 없는 상태에서 새로 시작”이 아니라,
`이미 있는 구조를 제품 acceptance 기준으로 재조정`
하는 문서다.

## 4. 제품 acceptance를 네 축으로 다시 정의

현재부터의 acceptance는 아래 네 축으로 본다.

### 4-1. Chart Acceptance

질문:

- 체크가 있어야 할 자리에 뜨는가
- 체크가 없어야 할 자리에 안 뜨는가
- `OBSERVE / PROBE / READY / BLOCKED`가 체감상 자연스러운가
- BTC / NAS / XAU가 너무 제멋대로 다르게 보이지 않는가

즉 chart acceptance는
`내가 차트만 봤을 때 이 scene이 왜 이렇게 보이는지 납득되는가`
를 뜻한다.

### 4-2. Entry Acceptance

질문:

- 실제 자동 진입이 “내가 여기서는 들어가도 된다”고 느끼는 자리에서 열리는가
- 들어가자마자 바로 adverse move를 자주 맞지는 않는가
- blocked여야 할 자리가 late guard나 누수로 열리고 있지는 않은가

즉 entry acceptance는
`이 자동 진입을 내가 승인할 수 있는가`
를 뜻한다.

### 4-3. Wait / Hold Acceptance

질문:

- 참아야 할 자리에서 너무 빨리 포기하지 않는가
- 반대로 그냥 버티면 안 되는 자리에서 의미 없이 오래 버티지 않는가
- directional wait와 neutral wait가 체감상 잘 구분되는가

즉 wait acceptance는
`시스템이 내 thesis를 얼마나 성급하거나 둔하게 다루는가`
를 뜻한다.

### 4-4. Exit Acceptance

질문:

- 청산이 너무 빠르지도, 너무 늦지도 않은가
- recovery / reverse / stop-up / partial이 내가 기대하는 성격으로 동작하는가
- hold -> exit로 넘어가는 이유가 실제로 납득되는가

즉 exit acceptance는
`내가 이 포지션을 여기서 정리하자고 느끼는 지점과 시스템이 얼마나 가까운가`
를 뜻한다.

## 5. 다섯 번째 축: Profit Sanity

중요한 점은 수익은 첫 번째 축이 아니라
마지막 sanity check라는 것이다.

이 문서는 수익을 무시하지 않는다.
다만 순서를 아래처럼 둔다.

```text
차트 acceptance
-> entry acceptance
-> wait acceptance
-> exit acceptance
-> 그 다음에 profit sanity
```

이유는 간단하다.
체감상 잘못된 시스템을 억지로 expectancy만 보고 유지하면
결국 다음 조정이 꼬이기 쉽기 때문이다.

## 6. 어떤 owner를 어떻게 건드려야 하나

### 6-1. Chart Acceptance owner

핵심 owner:

- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [chart_symbol_override_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_symbol_override_policy.py)

어떻게 건드리나:

- `consumer_check_state_v1`의 `check_stage / display_ready / display_score / repeat_count`를 조정한다
- painter는 의미를 새로 만들지 않고 시각 translation만 손본다
- must-show / must-hide / visually-similar casebook 기준으로
  upstream stage와 score를 다시 잠근다
- symbol balance는 override policy에서 조정한다

즉 chart acceptance는
`painter를 꾸미는 일`이 아니라
`upstream consumer state와 display ladder를 다시 맞추는 일`
이다.

### 6-2. Entry Acceptance owner

핵심 owner:

- [observe_confirm_router.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\core\observe_confirm_router.py)
- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [entry_probe_plan_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_probe_plan_policy.py)
- [entry_default_side_gate_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_default_side_gate_policy.py)

어떻게 건드리나:

- must-enter / must-block 사례를 먼저 casebook으로 고정한다
- late guard가 계속 핵심 진입질을 좌우하면 일부를 earlier gate로 당긴다
- probe ready 조건과 confirm 승격 조건을 family별로 다시 본다
- default side gate, conflict suppression, probe promotion을 다시 조인다
- 실제 adverse entry family를 기준으로 owner를 좁혀서 손본다

즉 entry acceptance는
`진입 점수 하나를 바꾸는 일`
이 아니라
`어떤 family가 실제로 열려도 되는지 계약을 다시 맞추는 일`
이다.

### 6-3. Wait / Hold Acceptance owner

핵심 owner:

- [wait_engine.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\wait_engine.py)
- [entry_wait_state_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_wait_state_policy.py)
- [entry_wait_decision_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_wait_decision_policy.py)
- [entry_wait_state_bias_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_wait_state_bias_policy.py)
- [entry_wait_edge_pair_bias_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_wait_edge_pair_bias_policy.py)
- [entry_wait_probe_temperament_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_wait_probe_temperament_policy.py)
- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)

어떻게 건드리나:

- `good patience / bad patience` 사례를 분리한다
- neutral wait와 directional wait를 다시 분리해 체감상 다르게 만든다
- hold patience, probe patience, noise tolerance를 family별로 본다
- 너무 빨리 exit pressure로 넘어가는 흐름을 casebook으로 잡는다

즉 wait acceptance는
`기다릴까 말까의 숫자 조정`
이 아니라
`어떤 thesis는 더 참아야 하고 어떤 thesis는 빨리 접어야 하는지`
를 다시 정의하는 일이다.

### 6-4. Exit Acceptance owner

핵심 owner:

- [exit_profile_router.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_profile_router.py)
- [exit_manage_positions.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_manage_positions.py)
- [exit_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_service.py)
- [exit_wait_state_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_wait_state_policy.py)
- [exit_reverse_action_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_reverse_action_policy.py)
- [exit_recovery_temperament_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_recovery_temperament_policy.py)
- [exit_stop_up_action_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_stop_up_action_policy.py)

어떻게 건드리나:

- `good exit / premature exit / late exit` casebook을 만든다
- reverse / recovery / partial / stop-up의 경계와 우선순위를 다시 잠근다
- hold에서 exit로 넘어가는 stage를 장면별로 다시 본다
- “계속 들고 갔어야 했나 vs 여기서 접는 게 맞았나”를 구분해서 다룬다

즉 exit acceptance는
`손절/익절 값을 조금 바꾸는 일`
이 아니라
`정리 방식의 성격을 다시 맞추는 일`
이다.

## 7. 무엇을 먼저 만들고 무엇을 나중에 보나

순서는 반드시 아래처럼 가는 게 좋다.

```text
Chart acceptance
-> Entry acceptance
-> Wait/Hold acceptance
-> Exit acceptance
-> Profit sanity
```

이유:

- chart가 이상하면 사용자가 체인을 신뢰하기 어렵다
- entry가 이상하면 이후 wait/exit 해석이 다 틀어진다
- wait가 이상하면 좋은 진입도 체감상 망가진다
- exit가 이상하면 전체 제품 느낌이 망가진다
- 수익은 이 네 축이 어느 정도 맞은 뒤에 보는 게 건강하다

## 8. 무엇은 하지 말아야 하나

이 reorientation 동안 아래는 하지 않는다.

- Position / Response / State / Evidence / Belief / Barrier 재설계
- semantic meaning owner 변경
- ML을 side/setup/exit owner로 승격
- auto-adaptation / self-tuning
- P7 size overlay를 먼저 main으로 밀기

즉 지금은 `더 똑똑한 엔진`을 만드는 게 아니라
`더 마음에 드는 제품 동작`을 만드는 것이다.

## 9. acceptance가 닫혔다는 뜻

아래가 보이면 acceptance가 닫힌 것으로 본다.

### Chart

- must-show / must-hide 오판이 크게 줄었다
- symbol별 체감 차이가 “의미 있는 차이”로 읽힌다

### Entry

- 최근 자동 진입을 봤을 때 “왜 여기서 열렸는지”를 납득할 수 있다
- immediate adverse entry family가 줄어든다

### Wait

- 참아야 할 자리는 더 참는다
- 그냥 버티는 구간은 줄어든다

### Exit

- premature exit와 late exit가 줄어든다
- reverse/recovery가 덜 어색해진다

### Profit sanity

- 이후 P1~P5 surface에서 expectancy와 alert pressure가 최소한 악화되지 않는다

## 10. 결론

이 문서의 핵심은 아래 한 줄이다.

```text
지금부터의 메인축은 구조 확장이나 자동 적응이 아니라,
차트 / 진입 / 기다림 / 청산을 내가 원하는 제품 동작으로 다시 맞추는 것이다.
```
