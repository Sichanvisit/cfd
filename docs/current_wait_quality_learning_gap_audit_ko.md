# 현재 Wait 품질 학습 Gap Audit

작성일: 2026-04-03 (KST)

## 1. 목적

이 문서는 지금 저장소 안에 이미 구축되어 있는 `wait` 관련 코드가 어디까지 와 있는지,
그리고 왜 체감상 `좋은 기다림 / 나쁜 기다림`이 아직 판단과 적용과 학습에 강하게 먹히지 않는 것처럼 느껴지는지를
한 번에 설명하기 위한 총정리 문서다.

핵심 질문은 두 가지다.

- 지금 시스템이 `wait`를 아예 구분하지 못하는가
- 아니면 구분은 하지만 그 차이가 `학습 가능한 정답`으로 충분히 올라가고 있지 않은가

이 문서의 결론은 두 번째에 가깝다.

## 2. 짧은 결론

지금 코드 기준으로는 `wait` 자체가 하나로 뭉뚱그려져 있지 않다.
오히려 런타임 판단층에서는 꽤 많이 나뉘어 있다.

하지만 그 차이가 `entry-side wait quality`라는 별도 사후 정답 체계로 강하게 올라가 있지는 않다.
그래서 실제 학습이나 라벨링 쪽에서는 아래 네 질문이 직접적으로 답되지 않는다.

- 기다렸더니 더 좋은 자리에서 들어갔는지
- 기다려서 손실을 피했는지
- 괜히 기다리다 신호를 놓쳤는지
- 기다렸는데 결국 더 나쁜 가격이나 더 늦은 손실이 되었는지

즉 지금의 문제는 `wait를 못 나눈다`가 아니라
`나눈 결과를 entry-side quality owner로 다시 모으지 못한다`에 가깝다.

## 3. 현재 이미 구축되어 있는 것

### 3-1. Wait 입력 정리와 context freeze

현재 wait는 그냥 `wait_score` 하나로만 판단되지 않는다.
먼저 컨텍스트를 묶는 과정이 있다.

관련 파일:

- `backend/services/entry_wait_context_contract.py`
- `backend/services/entry_wait_context_bias_bundle.py`
- `backend/services/entry_wait_state_policy_contract.py`

여기서 이미 다음 정보들이 묶인다.

- 현재 action / allowed action / required side
- observe reason / blocked by / action none reason
- box state / bb state
- setup status / trigger state
- wait score / conflict / noise / penalty
- energy helper hint
- layer mode hard block / suppressed 여부
- state / belief / edge-pair / probe bias 결과

즉 `wait`는 이미 단순 점수판이 아니라,
`왜 기다리고 있는지`를 설명하는 입력 묶음 위에서 판단되고 있다.

### 3-2. Wait state 분류

관련 파일:

- `backend/services/entry_wait_state_policy.py`
- `backend/services/wait_engine.py`

현재 wait state는 최소한 아래 정도로 나뉜다.

- `POLICY_BLOCK`
- `POLICY_SUPPRESSED`
- `AGAINST_MODE`
- `NEED_RETEST`
- `EDGE_APPROACH`
- `CENTER`
- `CONFLICT`
- `NOISE`
- `ACTIVE`
- `HELPER_SOFT_BLOCK`
- `HELPER_WAIT`

즉 이미 런타임 안에서는
`정책상 막힌 기다림`, `관찰형 기다림`, `중앙 잡음형 기다림`, `helper가 만든 기다림`이
서로 다른 것으로 취급되고 있다.

### 3-3. Wait decision 분류

관련 파일:

- `backend/services/entry_wait_decision_policy.py`

state가 정해진 뒤에도 그냥 전부 `wait`로 끝나지 않는다.
실제 decision은 다시 나뉜다.

- `wait_policy_hard_block`
- `wait_policy_suppressed`
- `wait_soft_helper_block`
- `wait_soft_helper_bias`
- `wait_hard_<state>`
- `wait_soft_edge_approach`
- `wait_soft_conflict_observe`
- `wait_soft_<state>`
- `skip`

즉 지금 엔진은 이미
`좋은 의미의 기다림`, `정책상 어쩔 수 없는 기다림`, `관찰용 보류`, `애매해서 스킵`을
다르게 처리하고 있다.

### 3-4. Row / runtime / hot payload 반영

관련 파일:

- `backend/services/entry_try_open_entry.py`
- `backend/services/storage_compaction.py`
- `backend/app/trading_application.py`
- `backend/services/runtime_signal_surface.py`

현재 row와 runtime 표면에는 이미 다음이 기록된다.

- `entry_wait_state`
- `entry_wait_reason`
- `entry_wait_decision`
- `entry_wait_selected`
- `entry_enter_value`
- `entry_wait_value`
- `entry_wait_context_v1`
- `entry_wait_bias_bundle_v1`
- `entry_wait_state_policy_input_v1`
- `entry_wait_energy_usage_trace_v1`
- `entry_wait_decision_energy_usage_trace_v1`

즉 `왜 wait가 되었는지`는 이미 런타임 표면에 꽤 자세히 남아 있다.

### 3-5. state25 / baseline에 일부 반영

관련 파일:

- `backend/services/teacher_pattern_labeler.py`
- `backend/services/teacher_pattern_pilot_baseline.py`

state25 labeler는 이미 `entry_wait_state`를 참고한다.
예를 들면 아래처럼 wait를 거친 의미가 pattern scoring에 반영된다.

- `passive_wait_context`
- `strong_reversal_wait`
- `confirm_pullback_context`

baseline 학습 feature에도 `entry_wait_state`가 categorical column으로 들어가 있다.

즉 wait 정보가 완전히 버려진 것은 아니다.

## 4. 그런데 왜 체감상 아직 별로인가

핵심 이유는 세 가지다.

### 4-1. wait는 state로 들어가지만 quality로 들어가지는 않는다

현재 baseline은 `entry_wait_state`를 feature로 쓴다.
하지만 이건 `무슨 종류의 wait였나` 정도만 알려준다.

반면 지금 필요한 것은 이쪽이다.

- 이 wait가 결과적으로 유익했는가
- 이 wait가 결과적으로 손해였는가
- 이 wait는 진짜 필요한 보류였는가
- 이 wait는 괜한 기회 상실이었는가

즉 현재는 `wait state`는 있지만 `wait outcome quality`는 약하다.

### 4-2. entry-side wait quality owner가 없다

현재 `good_wait / bad_wait / unnecessary_wait`는 있긴 있다.
하지만 이건 entry wait의 메인 owner가 아니다.

관련 파일:

- `backend/services/trade_csv_schema.py`
- `backend/services/csv_history_service.py`

지금 보이는 `wait_quality_label`은 주로
`exit / adverse wait / loss quality`와 연결된 사후 보조 라벨이다.

즉 `entry에서 기다린 판단` 자체를 직접 평가하는 owner는 아직 비어 있다.

### 4-3. offline outcome도 wait 중심이 아니라 trade outcome 중심이다

관련 파일:

- `backend/trading/engine/offline/outcome_labeler.py`

여기서 만드는 것은 주로 아래다.

- `buy_confirm_success_label`
- `sell_confirm_success_label`
- `false_break_label`
- `reversal_success_label`
- `continuation_success_label`
- `continue_favor_label`
- `fail_now_label`
- `recover_after_pullback_label`
- `better_reentry_if_cut_label`

이건 매우 중요하지만,
여전히 중심은 `들어간 뒤 결과`다.

반면 지금 필요한 것은
`기다렸기 때문에 생긴 결과`를 따로 평가하는 층이다.

## 5. 현재 구축된 것과 앞으로 구축해야 하는 것

### 현재 구축된 것

- wait 입력 contract
- wait bias bundle
- wait state 분류
- wait decision 분류
- wait energy trace
- runtime summary / surface 반영
- state25 및 pilot baseline으로의 부분 반영
- exit/loss 쪽 wait quality 보조 라벨

### 앞으로 구축해야 하는 것

- `entry_wait_quality_audit` owner
- entry wait의 사후 quality label
- `better_entry_after_wait`
- `avoided_loss_by_wait`
- `missed_move_by_wait`
- `delayed_loss_after_wait`
- 이 결과를 state25 / 후속 ML / 실험 보고서로 연결하는 bridge

## 6. 왜 이렇게 따로 구축되어야 하나

지금의 wait 엔진은 `판단 엔진`이다.
즉 지금 당장 들어갈지 기다릴지를 정한다.

하지만 지금 필요한 것은 `판단 평가 엔진`이다.
즉 그 wait가 나중에 보니 좋았는지 나빴는지를 판정해야 한다.

이 둘은 역할이 다르다.

- 판단 엔진이 live 의사결정을 담당
- 평가 엔진이 사후 학습 정답을 담당

이걸 같은 함수 안에 섞으면
live 코드가 복잡해지고,
나중에 라벨 기준을 바꾸기도 어려워진다.

그래서 `shadow audit -> closed history / report -> label / feature / experiment` 순서로
owner를 따로 세우는 것이 맞다.

## 7. 이번에 추가하는 새 owner

이번 턴에서 새로 추가하는 코드는 아래다.

- `backend/services/entry_wait_quality_audit.py`

이 파일은 아직 live 재판단을 하지 않는다.
대신 shadow audit 용 contract를 만든다.

지원하는 기본 label:

- `better_entry_after_wait`
- `avoided_loss_by_wait`
- `missed_move_by_wait`
- `delayed_loss_after_wait`
- `neutral_wait`
- `insufficient_evidence`

즉 이 파일은
`기다림을 좋다/나쁘다로 직접 평가하는 첫 owner`
라는 의미가 있다.

## 8. 다음에 이어서 해야 할 일

1. `entry_wait_quality_audit`를 recent wait row replay에 붙인다.
2. wait row와 이후 same-side next entry를 연결하는 bridge를 만든다.
3. closed history 또는 학습용 seed에 entry-side wait quality 컬럼을 추가한다.
4. state25 / baseline에 `entry_wait_quality_label` 또는 summary feature를 연결한다.
5. Step 9 쪽에는 `wait quality coverage`를 별도 watch 항목으로 추가한다.

## 9. 같이 읽으면 좋은 문서

- `docs/current_entry_wait_exit_lifecycle_summary_ko.md`
- `docs/current_wait_runtime_read_guide_ko.md`
- `docs/current_wait_architecture_reorganization_roadmap_ko.md`
- `docs/current_wait_quality_learning_design_ko.md`
- `docs/current_wait_quality_learning_implementation_roadmap_ko.md`
