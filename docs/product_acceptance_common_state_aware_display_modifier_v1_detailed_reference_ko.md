# Product Acceptance Common State-Aware Display Modifier v1 Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA 메인축의 첫 구현 단위인
`product_acceptance_common_state_aware_display_modifier_v1`
를 상세 기준으로 고정하는 문서다.

이 단계의 목적은 새 scene detector를 만드는 것이 아니다.
이미 존재하는

- `scene / probe_scene`
- `consumer_check_state_v1`
- BF bridge summary
- `chart_flow_policy`
- `chart_symbol_override_policy`

를 기준으로,
`scene owner + common state-aware modifier`
구조를 명시적으로 분리하는 것이다.

즉 이 문서의 핵심 질문은 아래다.

```text
어떤 자리는 scene이 의미를 결정하고,
어떤 부분부터는 bridge-aware modifier가 display 강도와 awareness를 조정하게 만들 것인가?
```

## 2. 왜 지금 이 문서가 필요한가

SF0~SF6와 BF1~BF7의 결론은 이미 고정되었다.

- raw surface는 이미 넓다
- 문제는 raw 부족보다 usage / value path / bridge였다
- BF bridge는 이미 만들어졌다
- 다음 메인축은 product acceptance 공통 modifier다

그런데 현재 chart acceptance 쪽 구현은 아직 아래 성격이 남아 있다.

- `consumer_check_state.py` 안에서 scene 판정과 display modifier가 함께 엉켜 있다
- BF1 bridge는 awareness preserve에만 좁게 붙어 있다
- `display_score`와 `display_repeat_count` ladder가 consumer 내부에 하드코딩되어 있다
- symbol별 예외가 scene 의미와 visibility 조정 사이에 함께 섞여 있다

즉 다음 단계의 핵심은
`더 많은 bridge를 추가하는 것`
보다
`기존 scene 의미와 modifier 책임을 분리해 공통 contract로 묶는 것`
이다.

## 3. 이 문서가 전제하는 현재 구현 상태

### 3-1. `consumer_check_state_v1`가 이미 chart acceptance의 실질 owner다

현재 [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 에서는
아래 값이 한 번에 결정된다.

- `check_candidate`
- `check_display_ready`
- `entry_ready`
- `check_side`
- `check_stage`
- `display_strength_level`
- `display_score`
- `display_repeat_count`

즉 scene 의미와 display 표현이 한 owner에 같이 있다.

### 3-2. BF1 bridge는 이미 live path에 일부 연결돼 있다

현재 [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 에는
`forecast_features_v1.metadata.bridge_first_v1.act_vs_wait_bias_v1`
를 읽는 `_act_wait_bridge_from_payload_v1(...)`가 있고,
soft wait awareness 보존에 제한적으로 사용된다.

즉 bridge-first는 이론이 아니라 이미 live path에 들어와 있다.
다만 사용 범위가 아직 매우 좁다.

### 3-3. 공통 display policy와 symbol override 경계도 이미 존재한다

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py) 에는
공통 expression / strength / visual ladder가 있고,
[chart_symbol_override_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_symbol_override_policy.py) 에는
아래 금지 원칙이 이미 있다.

- `meaning_override_forbidden = True`
- `strength_override_forbidden = True`
- `family_disable_forbidden = True`

즉 방향 자체는 이미 맞다.
지금 필요한 것은 이 경계를 실제 consumer/display path에 더 일관되게 반영하는 것이다.

## 4. 실제로 해결하려는 문제

현재 chart acceptance의 실제 병목은 아래다.

### 4-1. scene owner와 modifier owner가 분리돼 있지 않다

지금은
`이 자리가 어떤 자리인가`
와
`이 자리를 얼마나 강하게 / 약하게 / 억제해서 보여야 하는가`
가 같은 함수 흐름 안에서 같이 결정된다.

이 구조에서는

- must-show / must-hide 기준 고정이 어렵고
- bridge를 추가해도 어디에 먹는지 흐려지고
- symbol별 예외가 늘수록 이유 추적이 어려워진다

### 4-2. bridge가 공통 modifier가 아니라 point fix처럼 보인다

현재 BF1은 `bf1_awareness_keep`처럼 단일 adjustment reason으로 남는다.
이 방식은 첫 additive wiring으로는 맞았지만,
이제는
`bridge가 display modifier의 정식 입력`
으로 올라와야 한다.

### 4-3. symbol tuning이 공통 contract보다 앞에 보인다

XAU / NAS / BTC 조정은 이미 의미가 있었다.
하지만 다음 단계에서도 symbol별 예외만 계속 쌓으면,
다시
`왜 이 심볼만 이렇게 보이는가`
를 설명하기 어려워진다.

따라서 앞으로는

- 공통 modifier contract가 먼저
- symbol별 차이는 threshold / relief 강도만 제한적으로

라는 순서를 강하게 고정해야 한다.

## 5. v1에서 고정할 owner 분리

이 단계에서 가장 중요한 산출물은 아래 owner split이다.

### 5-1. Scene owner

scene owner는 아래만 책임진다.

- directional candidate 존재 여부
- `check_side`
- baseline `check_stage`
- `entry_ready`
- scene semantic reason
- hard block / structural block baseline

즉
`이 자리가 어떤 종류의 자리인가`
는 scene owner가 결정한다.

### 5-2. Modifier owner

modifier owner는 아래만 책임진다.

- awareness preserve 여부
- continuation / chop / conflict 구간 soft cap
- display ready visibility floor / suppression
- display strength level floor / cap
- display score floor / cap
- display repeat tempering
- modifier reason/debug surface

즉
`같은 자리라도 지금 얼마나 보여야 하는가`
는 modifier owner가 조정한다.

### 5-3. Painter owner

[chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py) 는
아래만 책임진다.

- event kind translation
- marker / line / brightness rendering
- repeat count 시각화

즉 painter는 의미 owner가 아니고,
modifier가 계산한 최종 surface를 그리는 쪽에 머문다.

### 5-4. Symbol override owner

[chart_symbol_override_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_symbol_override_policy.py) 는
아래만 허용한다.

- threshold multiplier
- support tolerance
- structural relief
- scene context relaxation
- visibility relief

즉 symbol override는
새 meaning을 만들거나 stage semantics를 바꾸지 않는다.

## 6. v1 modifier input contract

v1 modifier는 최소 아래 입력을 공통으로 받는다.

### 6-1. Baseline scene snapshot

반드시 필요:

- `check_candidate`
- `check_display_ready`
- `entry_ready`
- `check_side`
- `check_stage`
- `check_reason`
- `entry_block_reason`
- `blocked_display_reason`
- `display_box_state`
- `display_bb_state`
- `probe_scene_id`
- `display_importance_tier`

즉 modifier는 scene을 새로 만들지 않고,
기존 scene snapshot을 입력으로 받는다.

### 6-2. Runtime context

가능하면 같이 받는다.

- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `core_reason`
- `probe_reason`
- `canonical_symbol`

이 값들은 modifier reason을 설명 가능하게 만들기 위해 필요하다.

### 6-3. Bridge summary

v1에서 입력 대상으로 고정하는 bridge는 아래다.

- BF1 `act_vs_wait_bias_v1`

그리고 아래 bridge는 additive hook로 받을 수 있게 contract만 열어 둔다.

- BF2 `management_hold_reward_hint_v1`
- BF3 `management_fast_cut_risk_v1`
- BF4 `trend_continuation_maturity_v1`
- BF5 `advanced_input_reliability_v1`

즉 v1 첫 구현은 BF1 중심으로 시작하되,
contract는 이후 BF2~BF5가 같은 modifier path에 붙을 수 있게 설계한다.

## 7. v1 modifier output contract

v1 modifier의 canonical output은 아래처럼 둔다.

### 7-1. Effective display surface

- `effective_display_ready`
- `effective_stage`
- `effective_display_strength_level`
- `effective_display_score`
- `effective_display_repeat_count`

즉 painter와 downstream은
scene baseline이 아니라 modifier 적용 후 effective surface를 본다.

### 7-2. Modifier debug surface

- `modifier_contract_version`
- `modifier_reason_codes`
- `modifier_primary_reason`
- `modifier_applied`
- `modifier_score_delta`
- `modifier_stage_adjustment`

이 debug surface는
나중에 must-show / must-hide forensic과
chart acceptance snapshot review에서 바로 읽히게 해야 한다.

### 7-3. Consumer contract 호환 원칙

첫 구현에서는
기존 `consumer_check_state_v1` 필드명을 가능하면 유지한다.

즉 downstream 전체를 한 번에 바꾸기보다,
기존 필드 위에

- modifier debug 필드 추가
- scene baseline helper 분리
- effective surface 계산 path 분리

순으로 additive하게 간다.

## 8. v1에서 반드시 지켜야 할 구현 원칙

### 8-1. scene meaning을 modifier가 뒤집지 않는다

modifier는 아래를 하면 안 된다.

- side를 새로 생성
- candidate를 새로 생성
- hard block을 entry-ready로 뒤집기
- scene family를 symbol 예외로 바꾸기

### 8-2. BF bridge는 raw payload 대신 summary만 쓴다

modifier는 raw detector를 직접 끌어오지 않는다.
항상 bridge summary만 읽는다.

### 8-3. symbol별 차이는 threshold 중심으로만 남긴다

XAU / NAS / BTC의 차이는 유지될 수 있다.
하지만 그 차이는

- 문턱값
- relief 강도
- visibility cap/floor

수준에 머물러야 한다.

### 8-4. 하드코딩 relocation과 의미 변경을 동시에 하지 않는다

첫 구현에서 우선순위는
의미를 크게 바꾸는 것보다
owner split과 modifier contract를 분리하는 것이다.

즉 초기 구현은 additive wiring과 extraction 중심이 맞다.

## 9. 실제 작업 owner

이 단계의 핵심 owner는 아래다.

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [chart_symbol_override_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_symbol_override_policy.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)

검증 기준 파일은 아래를 우선 본다.

- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)

## 10. v1에서 아직 하지 않을 것

이 단계에서는 아래를 같이 하지 않는다.

- entry acceptance 재조정
- wait / hold acceptance 재조정
- exit acceptance 재조정
- broad raw add
- broad collector rebuild
- P7 overlay 재개
- full symbol casebook 재작성

즉 이 단계는
`chart acceptance 공통 modifier foundation`
에 집중한다.

## 11. 완료 기준

`product_acceptance_common_state_aware_display_modifier_v1`
는 아래를 만족하면 1차 close-out 가능하다.

1. scene owner와 modifier owner가 코드 구조상 분리된다
2. BF1 bridge가 point fix가 아니라 modifier 정식 입력으로 올라온다
3. `consumer_check_state_v1`가 modifier debug surface를 남긴다
4. symbol override는 threshold/relief 조정 쪽으로만 남는다
5. chart acceptance must-show / must-hide review에서 이유 추적이 지금보다 쉬워진다

## 12. 한 줄 요약

```text
PA의 다음 구현은 새 scene을 만드는 일이 아니라,
기존 scene owner 위에 BF bridge를 읽는 공통 state-aware display modifier를 세워
chart acceptance를 더 설명 가능하고 공통적인 구조로 바꾸는 일이다.
```
