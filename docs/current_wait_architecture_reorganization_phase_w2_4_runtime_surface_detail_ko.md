# 기다림 구조정리 Phase W2-4 상세 문서

부제: frozen wait contracts를 runtime, recent diagnostics, handoff 표면에 마감하기 위한 운영 surface 가이드

작성일: 2026-03-27 (KST)

## 1. 문서 목적

이 문서는 `W2-4`를 실제로 구현하기 전에,
지금까지 만들어 둔 wait 계약들

- `entry_wait_context_v1`
- `entry_wait_bias_bundle_v1`
- `entry_wait_state_policy_input_v1`

을 어디까지 어떤 형태로 운영 표면에 노출할지 정리하기 위한 문서다.

W2-1은 입력 context를 얼리는 단계였고,
W2-2는 bias/helper caller를 bundle로 묶는 단계였고,
W2-3는 state policy 입력면을 따로 고정하는 단계였다.

W2-4는 그 위에서
이 계약들을 사람이 실제로 읽는 surface로 마감하는 단계다.


## 2. 왜 W2-4가 필요한가

지금 구조는 내부적으로는 많이 좋아졌다.

- wait 입력 contract가 생겼다.
- bias가 개별 helper가 아니라 하나의 bundle로 묶였다.
- state policy 입력도 별도 contract로 빠졌다.
- metadata에는 compact context, bias bundle, state policy input이 남는다.

하지만 운영 관점에서는 아직 반쪽짜리다.

왜냐하면 지금 사람이 바로 읽기 쉬운 표면은 주로 아래에 머물러 있기 때문이다.

- `latest_signal_by_symbol`
- `recent_runtime_diagnostics`
- `recent_runtime_summary`
- handoff/checklist 문서

그런데 이 표면들에서는 아직
wait를 설명하는 중심 surface가 `wait_energy_trace_summary`에 다소 치우쳐 있다.

즉 지금은

> energy 쪽 설명은 좋아졌지만
> context / bias / state-policy input 쪽 설명은 운영 surface에 충분히 올라오지 않은 상태

에 가깝다.

이 상태로 멈추면 이런 일이 생긴다.

- "왜 wait였는가"를 다시 metadata/raw row를 열어 재구성해야 한다.
- recent diagnostics에서는 energy는 보이는데 policy-input면은 덜 보인다.
- 새 스레드 handoff에서 wait 해석이 다시 사람 머리 속 연결에 의존한다.


## 3. W2-3까지 이미 만들어진 것

W2-4를 설계할 때 중요한 건 이미 무엇이 있는지 분명히 보는 것이다.

### 3-1. row/metadata 수준 계약은 이미 있다

현재 wait state row에는 이미 아래 성격의 정보가 남는다.

- compact wait context
- bias bundle 요약
- state policy input 요약
- 최종 state policy 결과
- wait energy trace

즉 원재료는 있다.

### 3-2. recent diagnostics에도 wait-energy surface는 이미 있다

현재 runtime detail 쪽에는 이미
`wait_energy_trace_summary`가 recent window와 symbol summary 안에 들어간다.

이건 큰 진전이다.
다만 지금은 주로 "energy hint가 실제로 어디서 소비됐는가"를 보여주는 축이다.

### 3-3. handoff/checklist도 energy 읽는 법까지는 연결돼 있다

새 스레드 문서에는
`wait_energy_trace_summary`를 읽는 법이 이미 정리돼 있다.

즉 W2-4는 완전히 새 기반을 만드는 작업이 아니라,
이미 있는 contract들을 운영 surface로 더 끝까지 밀어 올리는 작업이다.


## 4. 현재 남아 있는 운영 surface의 부족한 점

### 4-1. wait-energy에 비해 wait-context 설명력이 약하다

지금 recent diagnostics는

- soft block이 많았는지
- helper wait bias가 많았는지
- state vs decision 어디서 많이 소비됐는지

를 잘 보여준다.

하지만 아직 아래는 한눈에 잘 안 보인다.

- 어떤 bias source가 많이 release를 만들었는지
- 어떤 bias source가 많이 wait lock을 만들었는지
- 어떤 special scene이 자주 보였는지
- state policy 입력면에서 어떤 이유 조합이 반복됐는지

즉 "energy 설명"은 좋아졌지만
"policy-input 설명"은 아직 얇다.

### 4-2. latest signal surface는 여전히 개별 row 읽기 중심이다

`latest_signal_by_symbol`는 현재 상태를 보여주지만,
거기서 바로

- 어떤 bias source가 활성화돼 있는지
- state policy input에서 무엇이 강한 요인인지
- special scene인지 아닌지

를 한 번에 읽기 좋은 compact surface는 아직 약하다.

### 4-3. recent summary는 count 중심이고 해석 축이 부족하다

현재 recent summary는

- stage counts
- blocked reason counts
- wrong ready count
- display ready summary
- wait-energy trace summary

위주다.

좋지만,
wait를 구조적으로 이해하려면 추가로 아래 해석 축이 필요하다.

- bias release/lock source counts
- state policy state/reason counts
- special scene counts
- threshold shift 요약

### 4-4. handoff 문서가 아직 energy 설명에 치우쳐 있다

지금 handoff/checklist는
wait-energy branch를 읽는 법은 많이 좋아졌다.

하지만 다음 질문에 대한 빠른 답은 아직 약하다.

- 최근 wait가 energy 때문이 아니라 edge-pair unresolved 때문인가?
- probe scene이라서 wait가 일반 case와 달랐는가?
- state policy input상으로는 center/noise/edge-approach 중 무엇이 우세했는가?


## 5. W2-4의 목표

W2-4의 목표는 한 문장으로 정리하면 아래와 같다.

> frozen wait contracts를 raw metadata 안에만 두지 말고,
> runtime/detail/slim/handoff에서 바로 읽을 수 있는 compact 운영 surface로 마감한다.

여기서 중요한 포인트는 두 가지다.

- raw payload를 더 많이 노출하는 것이 목적이 아니다.
- 사람이 최근 흐름을 빠르게 해석할 수 있도록 compact summary를 만드는 것이 목적이다.


## 6. W2-4에서 추천하는 운영 surface 층

W2-4는 한 곳에 다 쏟아붓는 방식보다,
각 층에 맞는 밀도로 나누는 편이 좋다.

### 6-1. Row / metadata 층

여기는 가장 상세한 compact truth를 남기는 층이다.

이미 있는 것:

- compact wait context
- compact bias bundle
- compact state policy input

여기서는 지금 구조를 유지하되,
필요하면 naming만 더 선명하게 맞춘다.

이 층은 "깊게 파고드는 진실 원문"이다.

### 6-2. `latest_signal_by_symbol` 층

여기는 개별 심볼의 현재 상태를 빠르게 읽는 층이다.

이 층에는 아래 정도의 compact surface가 적당하다.

- 현재 wait state / decision
- bias bundle compact summary
- state policy input compact summary
- special scene compact summary

단, full context 전체를 넣지는 않는 편이 좋다.

### 6-3. `recent_runtime_diagnostics` detail 층

여기는 최근 window를 진단하는 가장 중요한 운영 surface다.

여기에는 count/summary 중심으로 아래를 넣는 방향이 좋다.

- `wait_energy_trace_summary`
- `wait_bias_bundle_summary`
- `wait_state_policy_surface_summary`

이 층이 W2-4의 핵심이다.

### 6-4. `recent_runtime_summary` slim 층

slim 파일에는 detail 전체를 넣지 말고,
운영자가 지금 빠르게 방향만 보게 하는 요약만 넣는 것이 좋다.

예를 들면

- top release sources
- top wait-lock sources
- top policy states
- top special scenes

정도가 적당하다.

### 6-5. handoff / checklist 층

문서는 운영 surface를 읽는 안내서 역할을 해야 한다.

여기서는

- 어떤 경로를 먼저 열어야 하는지
- 어떤 summary를 먼저 읽어야 하는지
- 어떤 조합이면 energy 문제인지 / context 문제인지 / scene 문제인지

를 정리해 주는 것이 좋다.


## 7. W2-4에서 추천하는 새 summary 묶음

### 7-1. `wait_bias_bundle_summary`

이 요약은 recent window에서
"무슨 bias source가 wait를 풀었고, 무슨 source가 wait를 잠갔는가"를 보여준다.

추천 필드:

- `active_release_source_counts`
- `active_wait_lock_source_counts`
- `release_bias_count_distribution`
- `wait_lock_bias_count_distribution`

가능하면 symbol summary에도 같은 구조를 두는 것이 좋다.

### 7-2. `wait_state_policy_surface_summary`

이 요약은 recent window에서
"state policy 입력면과 결과면이 어떤 패턴으로 반복됐는가"를 보여준다.

추천 필드:

- `policy_state_counts`
- `policy_reason_counts`
- `required_side_counts`
- `policy_hard_block_active_rows`
- `policy_suppressed_rows`
- `helper_soft_block_rows`
- `helper_wait_hint_rows`

핵심은 복잡한 raw input 전체가 아니라,
운영 해석에 필요한 축만 모으는 것이다.

### 7-3. `wait_special_scene_summary`

이 요약은 특례 장면을 따로 모아서 보여준다.

추천 필드:

- `probe_scene_counts`
- `xau_second_support_probe_relief_rows`
- `btc_lower_strong_score_soft_wait_candidate_rows`
- `probe_ready_for_entry_rows`

이 summary가 있으면
"이건 일반 wait가 아니라 scene 특례가 많이 낀 흐름이다"를 빨리 판단할 수 있다.

### 7-4. `wait_threshold_shift_summary`

이 요약은 bias bundle이 실제 threshold를 얼마나 움직였는지 보여준다.

추천 필드:

- `soft_threshold_shift_avg`
- `hard_threshold_shift_avg`
- `soft_threshold_shift_up_rows`
- `soft_threshold_shift_down_rows`
- `hard_threshold_shift_up_rows`
- `hard_threshold_shift_down_rows`

이 summary가 있으면
"최근 wait가 많아진 게 raw score 문제인지 threshold shift 문제인지"를 분리해 볼 수 있다.


## 8. 무엇을 surface에 올리지 말아야 하나

운영 surface는 compact해야 한다.

그래서 아래는 가급적 recent summary에 직접 올리지 않는 편이 좋다.

- full `entry_wait_context_v1`
- full `entry_wait_state_policy_input_v1`
- full bias detail dict 전체
- raw observe/probe payload 전체

이런 것은 row metadata에 남겨 두고,
runtime recent summary에는 compact count/summary만 올리는 것이 맞다.


## 9. 추천 파일 범위

### 핵심 구현 파일

- `backend/app/trading_application.py`

여기서 recent window 진단을 집계하므로,
W2-4 핵심 구현은 이 파일에 들어갈 가능성이 높다.

### compact surface 조정 가능 파일

- `backend/services/storage_compaction.py`

`latest_signal_by_symbol`나 compact runtime row에
wait 관련 compact surface를 추가할 필요가 있으면 여기 조정이 필요할 수 있다.

### 문서 반영 파일

- `docs/thread_restart_handoff_ko.md`
- `docs/thread_restart_first_checklist_ko.md`

W2-4가 끝나면
wait-energy 읽는 법뿐 아니라
wait-bias / state-policy surface 읽는 법도 같이 적어야 한다.

### 테스트 대상 파일

- `tests/unit/test_trading_application_runtime_status.py`
- `tests/unit/test_storage_compaction.py`
- 필요하면 새 direct summary test 파일


## 10. 추천 구현 순서

### W2-4-1. recent diagnostics용 bucket 설계

먼저 `TradingApplication` 쪽에

- bias bundle bucket
- state policy surface bucket
- special scene bucket
- threshold shift bucket

을 설계한다.

이 단계에서는 shape를 먼저 고정하는 것이 중요하다.

### W2-4-2. accumulator / summary builder 추가

그 다음 recent rows를 돌면서
compact wait context, bias bundle, state policy input을 읽어
bucket을 채우고 summary를 만드는 helper를 추가한다.

### W2-4-3. detail/slim runtime payload 연결

그 다음

- `recent_runtime_diagnostics`
- `recent_runtime_summary`
- `recent_symbol_summary`

에 어떤 요약을 detail/slim으로 각각 넣을지 마감한다.

### W2-4-4. latest signal compact surface 검토

필요하면 `latest_signal_by_symbol` compact row에도
wait state-policy compact summary 일부를 넣는다.

다만 이건 recent diagnostics보다 후순위가 좋다.

### W2-4-5. handoff/checklist 문서 동기화

마지막으로
새 스레드에서 바로 읽을 수 있게 문서를 업데이트한다.


## 11. 이번 단계에서 건드리지 말아야 할 것

W2-4에서는 아래를 일부러 건드리지 않는 편이 좋다.

- wait state 분류 규칙
- bias 수치 조정
- state policy 로직 자체
- decision policy 로직
- exit/manage observability 확장

이번 단계는 어디까지나 운영 surface 마감이다.


## 12. direct 테스트에서 꼭 잡아야 할 것

### 12-1. recent diagnostics summary 테스트

최소한 아래를 direct test로 고정하는 것이 좋다.

- release source count가 제대로 집계된다
- wait-lock source count가 제대로 집계된다
- policy state/reason count가 제대로 집계된다
- special scene count가 제대로 집계된다
- threshold shift summary가 제대로 계산된다

### 12-2. symbol summary 분리 테스트

심볼별로
같은 window 안에서도 summary가 섞이지 않고 따로 집계되는지 고정해야 한다.

### 12-3. slim/detail 분리 테스트

detail에는 충분한 진단 정보가 남고,
slim에는 과도한 raw 정보가 실리지 않는지 확인해야 한다.

### 12-4. handoff 대상 경로 테스트 성격 점검

문서 테스트까지는 아니어도,
runtime payload shape가 handoff에서 그대로 읽을 수 있는 구조인지 확인하는 것이 좋다.


## 13. 완료 선언 조건

W2-4는 아래가 만족되면 완료로 볼 수 있다.

1. recent diagnostics에 wait context/bias/state-policy surface 요약이 추가된다.
2. symbol summary에도 같은 요약이 심볼별로 분리돼 남는다.
3. slim runtime summary에는 compact top-level 요약만 남는다.
4. row metadata와 recent diagnostics의 읽기 경로가 자연스럽게 이어진다.
5. handoff/checklist 문서가 새 surface 읽는 법까지 설명한다.


## 14. W2-4가 끝나면 좋아지는 점

W2-4가 끝나면 아래가 쉬워진다.

- 최근 wait가 energy 때문인지 context 때문인지 빠르게 분리
- probe/special scene 기반 wait가 많았는지 바로 확인
- state policy input 면에서 어떤 조합이 반복됐는지 빠르게 파악
- 새 스레드에서 CSV를 깊게 뒤지기 전에 방향을 바로 잡기

즉 W2-4가 끝나면 wait 구조는
내부 계약뿐 아니라 운영 surface까지도 한 언어로 읽히는 상태에 가까워진다.


## 15. 한 줄 결론

W2-4의 본질은
이미 만들어 둔 wait contracts를 raw metadata 안에만 두지 말고,
runtime recent diagnostics와 handoff에서 바로 읽을 수 있는 compact 운영 surface로 마감하는 것이다.
