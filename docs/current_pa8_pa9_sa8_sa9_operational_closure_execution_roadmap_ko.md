# PA8 / PA9 / SA8 / SA9 운영 닫기 실행 로드맵

## 목적

이 문서는 `PA8 / PA9 / SA8 / SA9`를 실제 운영에서 닫기 위한 실행 순서를 정리한다.

핵심 원칙은 아래 두 줄이다.

- **좁게**: gate / filter / symbol 하나씩 bounded review
- **넓게**: row / cycle / feedback를 지속 누적

즉 이 로드맵은 "무조건 더 만들기"가 아니라,
현재 남은 축만 좁히거나 넓혀서 운영을 채우는 방식으로 설계한다.

---

## 현재 출발점

현재 기준 출발점은 아래와 같다.

- `PA8`
  - NAS100 first symbol 집중
  - BTC/XAU는 watchlist
- `PA9`
  - packet/review/apply 통로 완성
  - actual handoff 사례 부족
- `SA8`
  - detector/feedback/propose 루프 연결 완료
  - semantic cluster / gate review 후보 surface 시작
- `SA9`
  - correction knowledge base row 생성 시작
  - cycle depth 부족

---

## 실행 원칙

### 원칙 1. PA는 "증거 가속"으로 닫는다

PA 쪽은 억지 판단보다 운영 증거를 빨리 채우는 것이 우선이다.

따라서:

- live row accumulation
- preview candidate 관찰
- rollback review
- pending approval 처리

를 우선한다.

### 원칙 2. SA는 "gate / cluster review"로 닫는다

SA 쪽은 로그가 이미 어느 정도 있으므로,
무턱대고 rollout을 늘리기보다 gate와 cluster를 review backlog로 줄여야 한다.

따라서:

- semantic cluster detector
- semantic gate review candidate
- feedback-aware priority
- correction knowledge

를 우선한다.

### 원칙 3. 완료 처리보다 bounded review를 우선한다

아래는 금지한다.

- sample floor 미달인데 완료 처리
- eligible row가 없는데 승격 성공 처리
- runtime idle 미충족인데 activation 성공 처리

대신 아래를 허용한다.

- 좁은 bounded candidate
- review backlog 승격
- one symbol / one gate / one filter lane 실험

---

## 단계별 실행 로드맵

## OC0. 기준면 고정

목적:

- 현재 상태를 한 번 더 흔들림 없이 고정

해야 할 일:

- latest board / runtime / audit snapshot 확인
- 현재 first symbol, pending approval, open positions 수 확인
- semantic cluster / gate 후보 최신 snapshot 고정

완료 기준:

- `PA8 / PA9 / SA8 / SA9` 현재 상태가 기준 snapshot으로 남음

---

## OC1. PA8 live window fill lane

성격:

- **넓게 채우기**

상세 기준:

- [current_oc1_pa8_live_window_fill_lane_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_oc1_pa8_live_window_fill_lane_detailed_plan_ko.md)

목적:

- PA8 closeout에 필요한 live evidence를 계속 쌓는다

대상:

- NAS100
- BTCUSD
- XAUUSD

핵심 관찰값:

- `observed_window_row_count`
- `sample_floor`
- `active_trigger_count`
- `first_window_status`
- `closeout_state`

운영 포인트:

- NAS100은 first symbol로 집중 관찰
- BTC/XAU는 watchlist 유지
- row가 안 쌓이는지, row는 있는데 preview candidate가 안 나오는지 분리

완료 기준:

- 최소 1개 symbol에서 sample floor에 유의미하게 접근
- live window ready symbol이 안정적으로 유지

---

## OC2. PA8 bounded preview filter review lane

성격:

- **좁게 실험하기**

목적:

- BTC/XAU에서 preview filter가 과도하게 좁은지 bounded review 후보를 만든다

대상:

- BTCUSD
- XAUUSD

입력:

- preview filter relaxation audit
- root cause audit

실행 방식:

- one symbol at a time
- one filter family at a time
- review-only / proposal-only 먼저

즉시 적용 금지:

- 전체 심볼 동시 완화
- threshold 일괄 완화
- review 없는 live apply

완료 기준:

- 최소 1개 filter family에 대해
  - review candidate가 backlog로 정리됨
  - 완화 여부를 판단할 근거가 생김

---

## OC3. PA8 rollback / approval cleanup lane

성격:

- **좁게 실험하기**

상세 기준:

- [current_oc3_pa8_rollback_approval_cleanup_lane_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_oc3_pa8_rollback_approval_cleanup_lane_detailed_plan_ko.md)

목적:

- NAS100의 `ROLLBACK_REQUIRED`와 governance backlog를 정리해서
  PA8 review 진행을 실제로 열 수 있게 한다

핵심 항목:

- pending approval
- rollback required
- approval backlog pending

운영 포인트:

- open positions와 충돌하지 않게 bounded하게 처리
- "왜 hold인지"와 "왜 rollback인지"를 분리 기록

완료 기준:

- pending approval backlog가 줄어듦
- NAS100 rollback review 근거가 정리됨

---

## OC4. PA9 first handoff preparation lane

성격:

- **넓게 채우기 + 좁게 review**

목적:

- PA8이 실제로 닫히는 순간 PA9 review/apply가 바로 이어질 수 있게 준비

핵심 관찰값:

- first symbol closeout/handoff status
- handoff review candidate
- handoff apply candidate

운영 포인트:

- PA8이 풀리기 전에는 handoff를 억지로 당기지 않음
- 대신 packet / review / apply 상태 전이를 계속 기록

완료 기준:

- first handoff review candidate 1회 이상 생성

---

## OC5. SA8 cluster feedback accumulation lane

성격:

- **넓게 채우기**

목적:

- semantic observe cluster를 detector feedback 학습 재료로 축적

대상:

- baseline no-action cluster
- scene trace unavailable cluster

운영 포인트:

- `/detect`
- `/detect_feedback`
- `/propose`

루프를 실제로 반복

완료 기준:

- semantic cluster detector가 실제 feedback을 받기 시작
- cluster 단위 confusion / promotion 근거가 생김

---

## OC6. SA8 semantic gate ablation lane

성격:

- **좁게 실험하기**

목적:

- semantic gate 중 어떤 문턱이 제일 먼저 review 가치가 있는지 좁혀본다

우선순위 후보:

1. `semantic_shadow_trace_quality = unavailable`
2. `blocked_by = energy_soft_block`
3. `action_none_reason = execution_soft_blocked`
4. `blocked_by = outer_band_guard`
5. `action_none_reason = probe_not_promoted`

운영 방식:

- gate 하나씩 review backlog에서 검토
- detector feedback과 `/propose` 결과를 같이 봄
- 바로 threshold 완화 대신 bounded review packet부터

완료 기준:

- 최소 1개 gate가 "유지 / 조정 후보 / 후순위" 중 하나로 분류됨

---

## OC7. SA8 activation discipline lane

성격:

- **넓게 관찰**

목적:

- activation ready 상태가 runtime idle 조건과 실제로 어떻게 충돌하는지 기록

핵심 관찰값:

- `activation_ready_count`
- `runtime_idle_flag`
- `open_positions_count`
- `approved_pending_activation`

운영 포인트:

- runtime idle이 아니면 억지 activation 금지
- user-managed open positions 문맥 유지

완료 기준:

- activation blocked 사례와 allowed 사례가 각각 최소 1회 이상 정리됨

---

## OC8. SA9 correction knowledge build lane

성격:

- **넓게 채우기**

목적:

- SA8 bounded rollout 결과를 correction knowledge base로 누적

필수로 쌓아야 하는 것:

- blocked pattern
- hold / rollback pattern
- success-like pattern

운영 포인트:

- cycle 수가 핵심
- 한두 번의 결과로 결론 내리지 않음

완료 기준:

- family / gate / threshold profile 단위 retrospective row가 쌓임
- 다음 bounded review에서 참고 가능한 지식이 생김

---

## OC9. 닫기 검토

목적:

- PA8 / PA9 / SA8 / SA9를 다시 한 번 같은 기준으로 평가

평가 질문:

1. PA8은 실제 closeout 사례가 있는가
2. PA9는 실제 handoff review/apply 사례가 있는가
3. SA8은 cluster/gate가 feedback과 proposal을 통해 좁혀졌는가
4. SA9는 correction knowledge가 다음 실험에 실제 도움을 주는가

이 단계에서만 "닫힘 / 추가 관찰 / 추가 review"를 결정한다.

---

## 좁게 vs 넓게 운영 표

| lane | 방식 | 현재 대상 | 목적 |
|---|---|---|---|
| OC1 PA8 live window fill | 넓게 | NAS/BTC/XAU | live evidence 누적 |
| OC2 PA8 preview filter review | 좁게 | BTC/XAU | filter 완화 후보 검토 |
| OC3 PA8 rollback/approval cleanup | 좁게 | NAS100 | review 진입 열기 |
| OC4 PA9 first handoff prep | 혼합 | NAS100 중심 | handoff 후보 생성 |
| OC5 SA8 cluster feedback | 넓게 | semantic cluster | detector 학습 입력 누적 |
| OC6 SA8 gate ablation | 좁게 | gate 1개씩 | 승격 막힘 원인 분해 |
| OC7 SA8 activation discipline | 넓게 | activation lane | idle/blocked 사례 축적 |
| OC8 SA9 correction knowledge | 넓게 | all rollout cycles | retrospective 지식 축적 |

---

## 지금 바로 실행 우선순위

현재 우선순위는 아래가 가장 자연스럽다.

1. `OC1` PA8 live window fill
2. `OC3` PA8 rollback / approval cleanup
3. `OC5` SA8 cluster feedback accumulation
4. `OC6` SA8 semantic gate ablation
5. `OC8` SA9 correction knowledge build
6. `OC4` PA9 first handoff preparation

이 순서의 의미는 아래와 같다.

- PA는 실제 closeout evidence를 먼저 만들고
- SA는 detector/proposal review를 먼저 쌓고
- 그 뒤 handoff와 correction knowledge가 뒤따른다

---

## 최종 결론

이 로드맵은 `PA8 / PA9 / SA8 / SA9`를
"각자 따로 끝내는 일"로 보지 않는다.

대신 아래처럼 본다.

```text
PA는 evidence acceleration으로 닫고
SA는 cluster/gate review와 correction knowledge로 닫는다
```

즉 지금부터의 운영은

- 충분한 사례를 넓게 채우고
- 선명한 막힘은 좁게 bounded review로 푼다

는 원칙으로 가야 한다.

이 방식이 현재 코드 구조와 운영 상태에 가장 잘 맞는 닫기 방식이다.
