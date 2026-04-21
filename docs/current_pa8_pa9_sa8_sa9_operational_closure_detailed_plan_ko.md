# PA8 / PA9 / SA8 / SA9 운영 닫기 상세 계획

## 목적

이 문서는 현재 CFD 프로젝트에서 아직 "구축은 되었지만 운영 완료로는 닫히지 않은" 네 축을
하나의 묶음으로 다시 정리하기 위한 상세 기준서다.

대상 축은 아래 네 가지다.

- `PA8 closeout`
- `PA9 handoff`
- `SA8 bounded semantic rollout`
- `SA9 correction knowledge base`

핵심 목적은 새 기능을 크게 추가하는 것이 아니다.

- 무엇이 이미 구축되었는지
- 무엇이 아직 live evidence 부족으로 막혀 있는지
- 무엇은 좁게 실험해야 하고
- 무엇은 넓게 관찰을 채워야 하는지

를 같은 언어로 묶어서, 운영 중에 단계별로 닫아갈 수 있게 만드는 것이다.

---

## 현재 한 줄 상태

현재 상태는 아래처럼 보는 것이 가장 정확하다.

- `PA8`
  - 구조는 거의 완료
  - live row와 rollback 정리가 부족
- `PA9`
  - handoff packet / review / apply 통로는 완료
  - PA8이 실제로 닫혀야 다음으로 감
- `SA8`
  - observe / detector / feedback / propose 루프는 구축 완료
  - live promotion / activation은 아직 evidence 부족
- `SA9`
  - correction knowledge base는 시작됨
  - 아직 bounded rollout cycle이 충분히 쌓이지 않음

즉 지금 단계는

```text
설계 추가 단계 < 운영 증거 채우기 단계
```

에 가깝다.

---

## 현재 구축도와 운영도

### PA8 closeout

- 구축도: `90~95%`
- 운영도: `35~45%`

현재 해석:

- `NAS100`은 first symbol로 올라와 있고 closeout review 직전까지 접근
- 하지만 sample floor 대비 live row가 아직 부족
- `BTCUSD`, `XAUUSD`는 activation 이후 row는 있으나 preview candidate로 잘 안 올라옴

현재 막힘:

- post-activation live row 부족
- preview filter가 좁음
- rollback required state가 남아 있음

### PA9 handoff

- 구축도: `90%`
- 운영도: `15~20%`

현재 해석:

- runtime / review / apply packet은 다 준비됨
- 그러나 `HOLD_PENDING_PA8_LIVE_WINDOW`
- 실제 handoff review candidate가 아직 없음

현재 막힘:

- PA8 closeout evidence 부족
- first symbol closeout이 아직 실제 완료 상태가 아님

### SA8 bounded semantic rollout

- 구축도: `80~85%`
- 운영도: `25~35%`

현재 해석:

- semantic cluster 관찰
- semantic gate review 후보
- `/detect -> /detect_feedback -> /propose`

까지는 이미 연결됨

하지만 live 쪽은 여전히

- `blocked_no_eligible_rows`
- `blocked_runtime_not_idle`

로 막혀 있다.

현재 막힘:

- `baseline_no_action`
- `semantic_unavailable`
- `outer_band_guard`
- `energy_soft_block`
- `probe_not_promoted`

### SA9 correction knowledge base

- 구축도: `70~75%`
- 운영도: `20~30%`

현재 해석:

- correction knowledge base는 이미 생성 중
- forced activation / disabled -> log_only 전환 같은 초기 row는 존재

하지만 아직 부족한 것:

- multiple bounded rollout cycle
- family / threshold profile 단위의 success pattern
- rollback outcome pattern

즉 SA9는 "구조는 시작됐지만 사례가 아직 얕다"가 정확하다.

---

## 왜 지금은 "좁게"와 "넓게"를 나눠야 하는가

현재 막힘은 크게 두 가지다.

1. 사례 자체가 부족한 축
2. 사례는 있는데 승격 가능한 좋은 사례가 부족한 축

이 두 축은 운영 방식이 달라야 한다.

### 넓게 채워야 하는 경우

아래 조건이면 넓게 관찰을 채우는 것이 먼저다.

- sample floor가 턱없이 부족
- 특정 심볼의 live row가 거의 없음
- rollout cycle 수가 적음
- correction knowledge row가 아직 얕음

이 경우는:

- more rows
- more cycles
- more observation windows

가 먼저다.

### 좁게 실험해야 하는 경우

아래 조건이면 좁은 bounded 실험이 먼저다.

- 사례는 있는데 특정 gate 때문에 계속 막힘
- preview filter가 일부 심볼에 과도하게 좁음
- baseline no-action 군집이 특정 cluster로 몰림
- detector/propose가 이미 같은 문제를 반복 surface함

이 경우는:

- one symbol
- one gate
- one filter family
- one bounded review lane

으로 좁혀서 실험해야 한다.

즉 현재 운영 방식은 아래처럼 정리된다.

```text
증거가 적으면 넓게 채우고
막힘 이유가 선명하면 좁게 실험한다
```

---

## 네 축을 하나의 운영 번들로 보는 기준

이 문서에서는 아래 번들을 하나의 "운영 닫기 세트"로 본다.

### 번들 A. PA 증거 가속 번들

대상:

- `PA8`
- `PA9`

목적:

- closeout evidence를 더 빠르게 얻고
- handoff가 실제 후보로 올라올 수 있게 만드는 것

포함:

- live row fill
- preview filter relaxation candidate
- rollback review
- pending approval 처리

### 번들 B. SA 승격 증거 번들

대상:

- `SA8`
- `SA9`

목적:

- semantic observe/no-action 군집을 detector/propose 학습 루프로 태우고
- semantic gate를 bounded review 대상으로 줄여가며
- correction knowledge를 쌓는 것

포함:

- cluster 관찰
- gate review candidate
- bounded activation discipline
- correction knowledge row 축적

---

## 각 축의 닫기 조건

### PA8 닫기 조건

최소 닫기 조건:

- 최소 1개 symbol에서 sample floor 충족
- live window 관찰이 실제로 존재
- rollback required state가 처리됨
- closeout review state가 `READY_FOR_REVIEW` 또는 그 이후로 진행
- closeout apply를 bounded하게 실제 1회 이상 완료하거나, 미적용이어도 hold 이유가 명확히 정리됨

보조 닫기 조건:

- BTC / NAS / XAU 중 적어도 2개 심볼에서
  - live row accumulation 또는
  - preview candidate flow가 정상적으로 관찰됨

### PA9 닫기 조건

최소 닫기 조건:

- first symbol 기준 PA8이 실제로 review/apply를 통과
- PA9 handoff review candidate가 최소 1회 생성
- PA9 handoff apply candidate가 최소 1회 생성 또는 hold 근거가 명확히 정리

보조 닫기 조건:

- handoff packet / review / apply packet의 상태 전이가 실제 라이브 사례로 기록

### SA8 닫기 조건

최소 닫기 조건:

- semantic cluster 관찰이 detector/feedback/propose 루프에서 실제 피드백을 받음
- semantic gate review 후보 중 최소 1개가 bounded review 대상이 됨
- eligible row가 최소 1회 이상 발생하거나, 발생하지 않아도 가장 큰 blocker가 구체적으로 좁혀짐
- runtime idle 조건에서 activation 시도 결과가 명확히 기록됨

보조 닫기 조건:

- `baseline_no_action` dominant cluster가
  - 유지될지
  - 좁혀질지
  - gate 조정 후보가 될지

가 feedback/proposal 기준으로 분리됨

### SA9 닫기 조건

최소 닫기 조건:

- correction knowledge base에 multiple rollout cycle 기반 row가 누적
- 적어도 아래 항목이 보임
  - one success-like pattern
  - one blocked pattern
  - one rollback/hold pattern

보조 닫기 조건:

- family / threshold-profile / gate type 별 retrospective pattern이 추출 가능해짐

---

## 지금 바로 운영에서 해야 하는 것

### 넓게 채우기

아래는 지금 당장 넓게 유지해야 한다.

- `PA8` live row accumulation
- `SA8` detect / feedback / propose 루프 반복
- `SA9` correction knowledge row 누적

이쪽은 조급하게 "완료 처리"로 밀면 안 된다.

### 좁게 실험하기

아래는 bounded하게 좁혀볼 수 있다.

- `PA8` BTC/XAU preview filter relaxation candidate
- `PA8` NAS rollback review
- `SA8` semantic gate review 후보
  - `semantic_shadow_trace_quality`
  - `energy_soft_block`
  - `execution_soft_blocked`
  - `outer_band_guard`
  - `probe_not_promoted`

즉 지금 운영의 좋은 기본 자세는 이거다.

```text
PA는 evidence acceleration
SA는 gate ablation + cluster feedback
```

---

## 지금 이 문서를 기준으로 한 운영 판단

현재 네 축은 모두 "막혀 있다"기보다,
막힘의 종류가 다르다.

- `PA8/PA9`
  - 운영 증거가 더 필요
- `SA8/SA9`
  - 승격 가능한 좋은 사례가 더 필요

그래서 지금 해야 할 일은 "억지 완료"가 아니라,

- PA는 증거가 더 빨리 생기게 하는 bounded review
- SA는 gate와 cluster를 학습 가능한 proposal backlog로 바꾸는 것

이다.

즉 이 문서의 결론은 아래와 같다.

```text
PA8 / PA9 / SA8 / SA9는 따로따로 닫는 것이 아니라
운영 증거 채우기 + bounded review + correction knowledge 축적으로 함께 닫아간다
```

---

## 연결 문서

- [current_pa789_roadmap_realignment_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_pa789_roadmap_realignment_v1_ko.md)
- [current_shadow_auto_system_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_shadow_auto_system_implementation_roadmap_ko.md)
- [current_pa8_non_apply_audit_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_pa8_non_apply_audit_detailed_plan_ko.md)
- [current_pa8_post_activation_root_cause_audit_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_pa8_post_activation_root_cause_audit_detailed_plan_ko.md)
- [current_pa8_preview_filter_relaxation_audit_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_pa8_preview_filter_relaxation_audit_detailed_plan_ko.md)
- [current_semantic_rollout_non_apply_audit_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_semantic_rollout_non_apply_audit_detailed_plan_ko.md)
- [current_semantic_baseline_no_action_cluster_detector_proposal_lane_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_semantic_baseline_no_action_cluster_detector_proposal_lane_detailed_plan_ko.md)
- [current_semantic_gate_review_candidate_lane_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_semantic_gate_review_candidate_lane_detailed_plan_ko.md)
