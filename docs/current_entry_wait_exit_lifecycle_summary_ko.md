# 현재 Entry-Wait-Exit Lifecycle Summary

작성일: 2026-03-29 (KST)

## 1. 이 문서의 목적

지금 시스템은 entry, wait, exit가 각각 따로 정리돼 있다.
하지만 실제 운영에서는 이 셋을 따로 읽기보다,
한 거래의 생애주기로 연결해서 읽어야 한다.

이 문서는 그 연결을 한 장으로 설명하기 위한 요약본이다.

## 2. 전체 흐름

### Entry

entry는 “지금 진입을 시도해도 되는가”를 정리하는 층이다.

- 관찰/확인 문맥이 먼저 정리된다.
- consumer check가 `ready / probe / observe / blocked`를 정한다.
- default side gate, probe plan, energy relief, late block이 그 위에 붙는다.
- 최종 진입 결과와 energy branch truth가 row와 runtime에 남는다.

entry를 읽을 때는 먼저 아래를 본다.

- `runtime_status.json.latest_signal_by_symbol`
- `consumer_check_stage`
- `blocked_by`
- `entry_decision_result_v1`

### Wait

wait는 “지금 바로 진입하지 않는다면 어떤 종류의 기다림인가”를 정리하는 층이다.

- state / belief / edge-pair / probe temperament bias가 모인다.
- wait state가 정해진다.
- wait decision이 `wait / skip`으로 갈린다.
- recent summary에서는 state, decision, bridge가 따로 보인다.

wait를 읽을 때는 먼저 아래를 본다.

- `recent_wait_state_semantic_summary`
- `recent_wait_decision_summary`
- `recent_wait_state_decision_bridge_summary`

그리고 더 깊게 보면 아래가 있다.

- `wait_energy_trace_summary`
- `wait_bias_bundle_summary`
- `wait_state_policy_surface_summary`
- `wait_special_scene_summary`
- `wait_threshold_shift_summary`

### Exit

exit는 “보유 포지션을 hold / recovery / reverse / exit_now 중 어디로 가져갈 것인가”를 정리하는 층이다.

- canonical exit context가 먼저 얼어 있다.
- exit wait state가 정해진다.
- utility decision이 최종 winner를 정한다.
- manage execution은 candidate -> plan -> result surface -> execute 형태로 이어진다.
- recent summary에서는 state family, decision family, bridge status가 보인다.

exit를 읽을 때는 먼저 아래를 본다.

- `recent_exit_state_semantic_summary`
- `recent_exit_decision_summary`
- `recent_exit_state_decision_bridge_summary`

## 3. 새 스레드에서 읽는 순서

권장 순서는 아래다.

1. `runtime_status.json`에서 latest signal과 recent summary를 본다.
2. entry가 막혔는지, wait가 많아졌는지, exit가 hold/recovery/reverse 어디로 기우는지 먼저 본다.
3. `runtime_status.detail.json`로 내려가서 해당 phase의 diagnostics를 본다.
4. 그래도 부족하면 마지막으로 `entry_decisions.csv`나 `trade_history.csv` row를 직접 본다.

## 4. 증상별로 어디를 먼저 봐야 하나

### 진입이 잘 안 된다

먼저 entry를 본다.

- `consumer_check_stage`
- `blocked_by`
- `recent_stage_counts`
- `recent_blocked_reason_counts`

### blocked는 아닌데 계속 기다림이 많다

먼저 wait를 본다.

- `recent_wait_state_semantic_summary`
- `recent_wait_decision_summary`
- `recent_wait_state_decision_bridge_summary`
- 필요하면 `wait_energy_trace_summary`

### 진입은 되는데 청산이 지나치게 느리거나 너무 빠르다

먼저 exit를 본다.

- `recent_exit_state_semantic_summary`
- `recent_exit_decision_summary`
- `recent_exit_state_decision_bridge_summary`

## 5. 지금 구축된 의미

지금 구조의 핵심은 “결과만 남는 시스템”이 아니라,
“각 phase가 왜 그렇게 됐는지의 핵심 의미가 계약으로 남는 시스템”이라는 점이다.

정확히는 아래가 가능해졌다.

- entry에서는 blocked / probe / ready 의미가 row와 runtime까지 남는다.
- wait에서는 좋은 기다림 / 나쁜 기다림 / helper-driven wait / skip이 summary로 남는다.
- exit에서는 hold / recovery / reverse / exit_now가 state family와 decision family로 남는다.

## 6. 같이 보면 좋은 문서

- `docs/thread_restart_handoff_ko.md`
- `docs/thread_restart_first_checklist_ko.md`
- `docs/current_wait_runtime_read_guide_ko.md`
- `docs/current_exit_runtime_read_guide_ko.md`
