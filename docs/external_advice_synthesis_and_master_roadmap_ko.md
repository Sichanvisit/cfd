# 외부 조언 종합 정리와 마스터 로드맵

작성일: 2026-03-29 (KST)

## 1. 이 문서의 목적

이 문서는 지금까지 외부 언어모델들과 주고받은 조언을
한 번에 잊지 않도록 정리하고,
현재 프로젝트의 실제 상태와 연결해서
"무엇을 이미 반영했고, 무엇을 다음 단계에서 해야 하며, 무엇은 더 나중에 해야 하는가"를
명확히 적기 위한 문서다.

핵심은 외부 조언을 그대로 받아 적는 것이 아니라,
우리 프로젝트의 현재 구조와 로드맵 위에
각 조언을 올바른 위치에 다시 배치하는 데 있다.


## 2. 먼저 큰 그림: 지금까지 대화의 축

지금까지의 대화는 사실 아래 세 단계 축으로 정리된다.

1. 프로젝트의 현재 구조를 정확히 설명하는 단계
2. 외부 조언이 현재 코드와 실제로 맞는지 걸러내는 단계
3. 앞으로 수익 개선과 운영 고도화로 어떻게 넘어갈지 정리하는 단계

이 흐름을 가장 짧게 말하면 아래와 같다.

- 지금까지는 "구조 구축" 단계였다.
- 이제부터는 "운영 관측과 수익 해석" 단계다.
- 그 다음은 "자기 인식과 제한적 자기 적응" 단계다.


## 3. 현재 기준 문서와 기존 실행 트랙의 위치

### 3-1. current_architecture_completed_work_summary_ko.md

이 문서는 "지금까지 무엇을 구축했는가"에 대한 문서다.
핵심 메시지는 아래와 같다.

- entry / wait / exit를 섞인 로직 덩어리에서 분리된 phase 구조로 끌어올렸다
- 각 phase에 입력 계약, owner, 결과 surface, runtime summary, 문서, 테스트를 붙였다
- 이제 시스템은 결과만 남는 엔진이 아니라 의미와 이유가 남는 엔진에 가까워졌다

즉 이 문서는 "구조 공사와 설명 가능성 확보"까지 왔다는 뜻이다.

### 3-2. current_profitability_operations_roadmap_ko.md

이 문서는 "다음에 무엇을 해야 하는가"에 대한 운영 로드맵 문서다.
핵심 메시지는 아래와 같다.

- 구조를 더 잘게 쪼개는 것보다 실제 기대값을 읽는 것이 중요하다
- lifecycle correlation, expectancy, alerting, compare, optimization loop가 다음 단계다
- 이미 만든 구조를 수익 개선과 운영 판단으로 연결해야 한다

즉 이 문서는 "운영 계기판과 수익 해석 계층"을 올리는 계획이다.

### 3-3. thread_restart_handoff_ko.md 와 consumer_coupled_check_entry_scene_refinement_roadmap_ko.md

이 두 문서는 우리가 실제로 지나온 중간 실행 트랙과
현재 현장 이슈를 붙잡는 기준선에 해당한다.

핵심 메시지는 아래와 같다.

- 이미 `R0 ~ R4` refinement와 acceptance / promotion-ready 정리는 상당 부분 끝났다
- 별도 트랙으로 `S0 ~ S6` consumer-coupled check / entry scene refinement를 진행했다
- 현재 scene display 구조 안정성은 많이 올라왔지만,
  최종 verdict는 `freeze`가 아니라 `hold and observe one more window`다
- 지금 가장 큰 미해결은 "표시가 예쁘냐"보다
  "실제 진입이 왜 직후 adverse move를 맞느냐" 쪽이다

즉 현재 위치를 정확히 말하면 아래와 같다.

- 큰 구조 공사는 이미 많이 끝났다
- chart / consumer / entry 연결도 상당 부분 정리됐다
- scene display 축은 관찰창을 한 윈도우 더 보는 단계다
- 다음 즉시 과제는 실제 체결 기준 entry timing / guard 품질 추적이다

이 점은 매우 중요하다.
왜냐하면 외부 조언을 로드맵에 반영할 때도
"아무것도 없는 상태에서 P0를 시작하는 것"이 아니라
"R0~R4와 S0~S6을 지나온 뒤 현재 현장 이슈를 해결하면서 P0~P7로 넘어가는 것"이기 때문이다.


## 4. 외부 조언들은 크게 세 부류였다

### A. 전략 일반론 조언

예: 세션 박스, 볼린저, 캔들 에너지를
"환경 / 필터 / 트리거"로 나누라는 조언.

이 조언의 의미는 아래와 같다.

- 전략 요소는 역할을 분리해서 써야 한다
- 과도하게 한 진입식에 다 넣지 말아야 한다
- 비용, 세션, 슬리피지, 검증이 중요하다

이 조언은 원칙으로는 맞지만,
우리 프로젝트는 이미 단일 박스-볼린저 전략 수준을 넘은 semantic framework이므로,
직접적인 구현 로드맵이라기보다
"역할 분리 원칙" 정도로 받아들이는 것이 맞다.

### B. 아키텍처/추적성 조언

예: 아래 같은 조언들.

- 의미 레이어 분리는 강점이다
- consumer contract를 지켜야 한다
- ContextClassifier가 너무 많은 책임을 가진다
- legacy scorer와 semantic engine의 관계를 명확히 해야 한다
- decision trace가 필요하다
- forecast calibration과 belief decay 검증이 중요하다

이 조언은 우리 프로젝트의 현재 구조와 가장 직접적으로 맞닿아 있다.
즉 이 부류가 현재 가장 실무적으로 중요하다.

### C. 상위 운영/자기 인식 조언

예: 아래 같은 조언들.

- meta-cognition
- archetype health tracking
- distribution drift detection
- counterfactual engine
- semantic-aware sizing
- closed-loop adaptation
- system anomaly detection

이 조언은 방향은 매우 좋지만,
현재 운영 로드맵(P1~P5)보다 한 단계 위의 이야기다.
즉 이 조언은 지금 당장 코어 semantic layer에 넣는 것이 아니라,
운영 관측 로드맵이 어느 정도 완성된 뒤
P6~P7 단계에서 다루는 것이 맞다.


## 5. 외부 조언에서 끝까지 기억해야 할 핵심

외부 조언들을 다 걷어내고 남는 공통 핵심은 아래 10개다.

1. 새 semantic layer를 계속 추가하는 것이 정답은 아니다.
2. 역할 분리와 consumer contract 유지가 가장 중요하다.
3. 결과보다 "왜 그런 결과가 나왔는가"가 남아야 한다.
4. 구조가 좋아도 expectancy를 숫자로 읽지 못하면 수익 개선으로 못 간다.
5. 최근 변화와 이상 징후를 사람이 늦게 보기 전에 잡아야 한다.
6. forecast와 confidence는 검증되기 전까지 과신하면 안 된다.
7. belief, barrier, forecast 같은 후반 레이어는 calibration과 sensitivity가 중요하다.
8. 크기 조절(position sizing)은 나중에 붙여도 PnL 영향은 매우 크다.
9. 자기 적응(auto-adaptation)은 가장 마지막 단계여야 한다.
10. 상위 1%로 가는 차이는 시장 해석 자체보다 자기 해석의 품질을 감시하는 데서 난다.


## 6. 조언 항목별 현재 판단

아래 표는 외부 조언을 현재 프로젝트 기준으로 다시 분류한 것이다.

| 항목 | 현재 판단 | 설명 |
|---|---|---|
| 의미 레이어 분리 | 이미 반영됨 | Position → Response → State → Evidence → Belief → Barrier 축은 이미 핵심 foundation으로 자리잡았다. |
| consumer contract 유지 | 이미 반영됨 | observe/confirm handoff와 consumer boundary freeze가 현재 구조의 핵심 원칙이다. |
| entry/wait/exit를 phase 구조로 정리 | 이미 반영됨 | 구조 문서가 말하는 현재까지의 핵심 성과다. |
| decision trace | 즉시 착수 필요 | 지금 가장 큰 부족분 중 하나다. 구조는 있는데 설명 한 줄이 아직 부족하다. |
| legacy scorer ↔ semantic 관계 명시 | 즉시 착수 필요 | 공존 상태가 해석 비용을 키우므로 ownership을 분명히 해야 한다. |
| ContextClassifier 내부 분해 | 단계적 착수 필요 | 현재 가장 큰 구조 리스크지만, contract를 깨지 않도록 천천히 분해해야 한다. |
| lifecycle correlation observability | 다음 단계 핵심 | 운영 로드맵 P1의 중심 과제다. |
| expectancy / attribution | 다음 단계 핵심 | 운영 로드맵 P2의 중심 과제다. |
| anomaly detection / alerting | 다음 단계 핵심 | 운영 로드맵 P3의 중심 과제다. |
| time-series comparison | 다음 단계 핵심 | 운영 로드맵 P4의 중심 과제다. |
| optimization loop / casebook | 다음 단계 핵심 | 운영 로드맵 P5의 중심 과제다. |
| chart / consumer / entry scene display 안정화 | 거의 완료 + 관찰 필요 | S0~S6을 거치며 구조 안정성은 많이 올라왔지만 최종 verdict는 아직 one more window 관찰이다. |
| 실제 entry timing / guard 품질 추적 | 즉시 착수 필요 | 현재 가장 큰 미해결은 scene display보다 실제 진입 직후 adverse move 문제다. |
| archetype health / meta-cognition | P6 이후 | 운영 데이터가 쌓인 후에 의미가 생기는 상위 운영 계층이다. |
| semantic-aware sizing | P6 이후 | 기대값과 health 해석이 생긴 후에 붙일수록 안정적이다. |
| drift detection | P6 이후 | 운영 기준면이 먼저 있어야 drift를 의미 있게 읽을 수 있다. |
| counterfactual engine 확장 | P6~P7 | shock-counterfactual 씨앗은 있으나 일반 엔진은 더 나중이 맞다. |
| closed-loop adaptation | 가장 마지막 | 잘못 붙이면 시스템이 자기 노이즈를 강화할 수 있다. |
| forecast calibration hardening | 횡단 과제 | P2 이후 계속 병행해야 하는 검증 과제다. |
| belief decay sensitivity | 횡단 과제 | trace와 expectancy가 생긴 뒤 병행하는 검증 과제다. |
| formal global state machine | 선택 과제 | transition audit만으로 충분하면 꼭 필요한 건 아니다. |
| layer value ablation | 연구 과제 | 운영 기준면이 충분히 선 뒤 구조 단순화 판단용으로 사용한다. |


## 7. 우리가 취해야 할 기본 원칙

앞으로 어떤 개선을 하더라도 아래 원칙은 깨지 않는 것이 좋다.

### 7-1. semantic owner를 함부로 늘리지 않는다

새 레이어를 넣기 전에
"이걸 기존 layer의 metadata / diagnostics / overlay로 처리할 수 없는가"를 먼저 본다.

### 7-2. consumer boundary를 흔들지 않는다

meta-cognition, health, drift, sizing 같은 상위 기능이 들어오더라도
observe/confirm identity와 archetype/invalidation/management contract는 쉽게 바꾸지 않는다.

### 7-3. 자동 조정은 가장 늦게 붙인다

처음에는 읽기, 요약, 비교, 경고만 한다.
그 다음에 제한적 size/confidence penalty를 넣는다.
마지막에야 threshold나 policy를 자동으로 조정한다.

### 7-4. 운영 계층은 semantic layer 위의 overlay로 붙인다

meta-cognition이나 drift는
semantic owner 자체가 아니라
운영 overlay 또는 policy overlay로 붙이는 것이 안전하다.

### 7-5. 확률처럼 보이는 score를 진짜 확률처럼 쓰지 않는다

forecast, confidence, health score는
calibration이 확보되기 전까지는 bounded score로 취급하는 것이 맞다.


## 8. 마스터 로드맵: R0-B + P0 ~ P7

아래 로드맵은 현재 두 문서와 외부 조언을 모두 합친 최종 축이다.

### R0-B. 현재 즉시 대응 하위 단계: Actual Entry Forensics

목표:
최근 자동진입 후 즉시 역행하거나 짧게 손실 청산되는 사례를
실제 체결 기준으로 다시 추적한다.

현재 구현 상태:

- `R0-B1 sample extraction` 완료
- `R0-B2 decision row matching` 완료
- `R0-B3 forensic table normalization` 완료
- `R0-B4 family clustering` 완료
- `R0-B5 action candidate derivation` 완료
- 최신 기준선:
  `sample 30 / matched 7 / exact 0 / fallback 7 / unmatched 23`
  `forensic row 30 / coverage_gap 23 / fallback_match 7`
  `family 4 / decision_log_coverage_gap 23 / consumer_stage_misalignment 3 / guard_leak 2 / probe_promoted_too_early 2`
  `action candidate 4 / critical 1 / high 3`
  `detail history + archive-aware reader 추가 후에도 earliest coverage = 2026-03-27T15:29:43`
- 현재 발견된 핵심 이슈:
  `exact_runtime_snapshot_key` 중 일부가
  `anchor_value=0.0` 형태의 generic runtime key 재사용 가능성을 보인다
  그리고 현재 남은 큰 축은
  매처 기능 부족보다 `decision source retention/backfill` 부재에 더 가깝다

즉, 지금부터의 중심은
`샘플을 더 뽑는 것`보다
`B2 결과를 forensic truth table로 정규화해서
generic linkage와 진짜 linkage를 분리하는 것`이었고,
그 단계는 완료됐다.

이제 다음 중심은
`decision log coverage`를 먼저 메우고,
coverage 안쪽에 남은 `consumer/guard/probe leakage`를
실제 수정 대상으로 좁히는 것이다.

추가 최신 상태:
- `decision_log_coverage_gap`은
  archive-aware forensic read까지 구현됐고,
  현재는 실제 source retention/backfill 과제로 남아 있다.
- `consumer_stage_misalignment`는
  `consumer_open_guard_v1`와 order submit 직전 hard-stop이 들어간 상태다.
- `guard_leak`는
  `entry_blocked_guard_v1`와 strict guard set 기반 submit 직전 hard-stop이 들어간 상태다.
- `probe_promoted_too_early`는
  `probe_promotion_guard_v1`와 probe-plan not-ready 기반 submit 직전 hard-stop이 들어간 상태다.
- R0-B close-out과 다음 active next step은 아래 문서에 고정했다.
  - [refinement_r0_b6_close_out_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b6_close_out_handoff_ko.md)
  - [decision_log_coverage_gap_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_detailed_reference_ko.md)
  - [decision_log_coverage_gap_execution_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_execution_roadmap_ko.md)
- `decision_log_coverage_gap`의 `C0 baseline freeze`는 구현 완료 상태이며,
  현재 active next step은 `C1 source inventory / retention matrix`다.

이 단계가 필요한 이유:

- 현재 현장 문제의 중심은 `scene display`보다 `실제 entry quality`에 있다
- S0~S6이 chart / check / consumer 결속을 정리했다면,
  R0-B는 그 위에서 "왜 잘못 열린 entry가 존재하는가"를 바로 잡는 단계다
- 이건 새로운 독립 phase가 아니라, 이미 완료된 R0 기준선을 현재 actual entry 문제에 다시 연결하는 하위 단계다

핵심 과제:

- 최근 손실 / 짧은 보유 청산 체결 추출
- 직전 `entry_decisions.csv` 매칭
- 공통 `setup_id / observe_reason / blocked_by / consumer_check_stage` 식별
- actual adverse move와 연결된 entry gate / guard / exit timing 패턴 추적
- 필요 시 해당 family의 entry gate 조정

완료 기준:

- "들어간 직후 반대로 가는 진입"의 공통 family와 guard 누수 지점을 최소 한 번 이상 설명 가능하다
- display 문제가 아니라 실제 entry gate 문제였는지, 또는 exit timing 문제였는지 방향을 잡을 수 있다

### P0. 아키텍처 안정화와 추적성 보강

목표:
현재 구조를 흔들지 않으면서 설명 가능성과 ownership을 먼저 강화한다.

핵심 과제:

- decision trace 추가
- legacy scorer ↔ semantic 관계 명시
- ContextClassifier façade 유지형 내부 분해 시작
- consumer audit/logging 정리

완료 기준:

- "왜 진입/비진입/대기/청산이 나왔는가"를 한 줄 trace로 따라갈 수 있다
- legacy와 semantic 중 누가 최종 판단권자인지 명시적으로 볼 수 있다

### P1. Lifecycle Correlation Observability

목표:
entry, wait, exit를 따로 보지 않고 거래 생애주기로 이어서 읽는다.

핵심 과제:

- entry-wait-exit correlation summary
- symbol별 lifecycle 연결 요약
- blocked reason / state family / decision family 연동 집계

완료 기준:

- 최근 손실이 entry 문제인지, wait 문제인지, exit 문제인지 방향을 한 번에 잡을 수 있다
- R0-B에서 본 adverse entry case를 lifecycle 흐름 안에서 반복적으로 읽을 수 있다

### P2. Expectancy / Attribution Observability

목표:
무엇이 실제 기대값을 만드는지 숫자로 읽는다.

핵심 과제:

- setup별 expectancy
- regime별 expectancy
- symbol별 expectancy
- entry/wait/exit stage별 PnL attribution
- exit family별 성과 요약

완료 기준:

- 무엇을 늘리고 줄일지 감이 아니라 숫자로 말할 수 있다
- 특히 "직후 adverse move family"를 expectancy 하위 그룹으로 분리해서 읽을 수 있다

### P3. Alerting / Anomaly Detection

목표:
이상 징후를 사람이 늦게 보기 전에 먼저 감지한다.

핵심 과제:

- wrong ready, bridge mismatch, wait selected rate, reverse now 급증 경보
- runtime unavailable / diagnostics missing 경보
- 운영자용 경고 surface 설계

완료 기준:

- 운영자가 직접 파일을 열기 전 이상 패턴을 먼저 인지할 수 있다

### P4. Time-Series Comparison

목표:
오늘과 어제, 변경 전후를 비교해서 개선/악화를 빠르게 판단한다.

핵심 과제:

- recent window 비교
- 배포 전후 비교
- symbol/setup/regime 변화량 요약
- wait/exit family 비율 변화량 요약

완료 기준:

- 변경 이후 무엇이 좋아졌고 나빠졌는지 방향을 즉시 읽을 수 있다

### P5. Optimization Loop / Casebook 강화

목표:
운영 데이터를 다시 구조 개선과 튜닝 입력으로 돌려준다.

핵심 과제:

- 대표 승률 장면 casebook
- 대표 손실 장면 casebook
- regime별 best / worst scene
- setup blacklist / caution list
- tuning candidate queue

완료 기준:

- 손실과 성공 장면이 단순 회고가 아니라 다음 정책 개선 입력으로 바로 연결된다
- 기존 S1/S2 must-show / must-hide casebook이 이제 실제 PnL casebook과 연결된다

### P6. Meta-Cognition / Health / Drift / Sizing

목표:
시스템이 자기 상태와 최근 건강도를 읽고,
그 결과를 confidence와 size에 반영하게 한다.

핵심 과제:

- archetype health tracker
- recent system confidence summary
- distribution drift detection
- semantic-aware size overlay
- health/drift 기반 confidence penalty

완료 기준:

- 같은 archetype이라도 최근 건강도와 drift 상태에 따라 더 보수적 또는 공격적으로 운영할 수 있다

### P7. Controlled Counterfactual / Selective Adaptation

목표:
대안 행동을 비교하고,
안전장치 아래에서 제한적으로 운영 파라미터를 조정한다.

핵심 과제:

- entry/exit 일반 counterfactual 확장
- safe adaptation proposal
- rollback / cap / min evidence / cooldown guard
- partial live 수준의 선택적 자기 적응

완료 기준:

- "다르게 했으면 어땠는가"를 체계적으로 보고
- 충분한 근거가 있는 경우에만 제한적으로 운영 파라미터를 조정할 수 있다


## 9. 현재 위치를 정확히 잡으면 이렇게 된다

현재 위치는 아래처럼 정리하는 것이 가장 정확하다.

- `R0 기준선`: 완료
- `R0-B`: 지금 가장 현실적인 즉시 대응 하위 단계
- `R1 ~ R4`: 완료
- `S0 ~ S6`: 구현 완료, 최종 verdict는 `hold and observe one more window`
- `P0 ~ P2`: R0-B와 병행해서 준비 / 착수할 다음 상위 단계
- `P3 ~ P5`: 운영 관측과 수익 해석 고도화
- `P6 ~ P7`: 자기 인식과 제한적 자기 적응

즉 우리는 지금
"구조를 만드는 단계"는 상당 부분 지나왔고,
"scene display 안정화의 마지막 관찰 단계"와
"실제 entry quality forensic을 위해 R0를 다시 적용하는 단계" 사이에 서 있다고 보면 된다.

### R / S / P 매핑표

| 축 | 뜻 | 현재 상태 | 성격 | 다음 연결 |
|---|---|---|---|---|
| `R0` | reason / key / non-action 정합성 최소셋 | 완료 | trace 해석 기준선 | 이후 모든 refinement와 운영 해석의 바닥 |
| `R0-B` | actual entry forensic 재가동 | 현재 즉시 대응 하위 단계 | 실체결 기준 adverse entry 원인 추적 | P0/P1/P2의 현장 기준선 |
| `R1` | Stage E 미세조정 | 완료 | symbol / stage 체감 균형 보정 | R2로 넘어가기 전 체감 튜닝 마감 |
| `R2` | storage / export / replay / dataset join 정합성 | 완료 | 데이터 연결선 고정 | R3 ML refinement의 바닥 |
| `R3` | semantic ML refinement + shadow/source cleanup | 완료 | ML 품질 / provenance / compare 정리 | R4 acceptance / promotion-ready 기반 |
| `R4` | acceptance / promotion-ready / allowlist 운영 | 완료 | bounded live 운영 정리 | 이후 운영 판단과 확장 로드맵의 기준선 |
| `S0` | scene baseline snapshot | 완료 | consumer-coupled scene refinement 시작점 | must-show / must-hide 논의 출발점 |
| `S1` | must-show scene casebook | 완료 | 보여야 하는 장면 고정 | scene contract 정교화 |
| `S2` | must-hide scene casebook | 완료 | 숨겨야 하는 장면 고정 | scene contract 정교화 |
| `S3` | visually similar alignment audit | 완료 | 비슷해 보이는 장면 간 의미 차이 정리 | S4 contract refinement 근거 |
| `S4` | consumer_check_state contract refinement | 완료 | chart/check/entry 의미 정렬 | S5 symbol tuning 기반 |
| `S5` | symbol balance tuning | 완료 | BTC/NAS/XAU 체감 균형 조정 | S6 acceptance 직전 조정 |
| `S6` | scene refinement acceptance | 구현 완료, 최종 verdict는 hold | 구조 안정성 검증 | 한 윈도우 더 관찰 |
| `P0` | 아키텍처 안정화와 추적성 보강 | 다음 즉시 상위 단계 | decision trace / ownership / internal split | P1/P2 해석력을 높임 |
| `P1` | lifecycle correlation observability | 다음 핵심 단계 | entry-wait-exit를 거래 생애주기로 읽기 | 손실 원인 위치 파악 |
| `P2` | expectancy / attribution observability | 다음 핵심 단계 | 무엇이 실제 기대값을 만드는지 수치화 | 수익 개선 판단 기준 생성 |
| `P3` | alerting / anomaly detection | 운영 확장 단계 | 이상 징후 자동 감지 | 늦은 발견 방지 |
| `P4` | time-series comparison | 운영 확장 단계 | 전후 비교와 변화량 읽기 | 개선/악화 판단 속도 향상 |
| `P5` | optimization loop / casebook 강화 | 운영 해석 마감 단계 | 회고를 튜닝 입력으로 연결 | P6~P7의 바닥 |
| `P6` | meta-cognition / health / drift / sizing | 상위 운영 단계 | 시스템이 자기 상태를 읽고 보수성 조절 | 자기 인식 계층 |
| `P7` | controlled counterfactual / selective adaptation | 최상위 단계 | 대안 비교와 제한적 자기 적응 | 신중한 자동 운영 |


## 10. P5까지와 P6~P7의 차이

이 차이는 꼭 기억할 필요가 있다.

### P5까지

- 사람이 더 잘 읽고 운영하고 개선할 수 있게 만드는 단계
- 운영 가시성, 기대값 해석, 이상 감지, 비교, 케이스 축적이 중심이다

### P6~P7

- 시스템도 자기 상태를 읽고 일부를 조정하게 만드는 단계
- health, drift, sizing, counterfactual, 제한적 adaptation이 중심이다

즉 외부 조언 중
"상위 1%로 가려면" 계열의 조언은
대부분 P6~P7 축에 해당한다.


## 11. 지금 당장 가장 좋은 시작점

현재 시점에서 가장 좋은 첫 작업은 아래 다섯 가지다.

1. 최근 손실 / 짧은 보유 청산 체결에서 R0-B actual entry forensic 추출
2. decision trace 설계 문서 초안 작성
3. legacy scorer ↔ semantic relation 명시 방식 설계
4. lifecycle correlation summary shape 설계
5. setup / regime / symbol expectancy summary shape 설계

이 다섯 가지가 붙으면
R0-B와 P0, P1, P2가 동시에 선명해지고,
이후 P3~P7도 훨씬 덜 흔들린다.


## 12. 마지막 정리

우리가 지금까지 해온 방향은 일관됐다.

- 처음에는 구조를 만들었다
- 그다음에는 chart / consumer / entry를 같은 체인으로 더 강하게 묶었다
- 지금은 scene display를 한 윈도우 더 관찰하면서 실제 entry quality를 forensic으로 다시 본다
- 다음에는 무엇이 실제로 돈을 벌고 잃는지 읽을 것이다
- 마지막에는 시스템이 자기 상태를 읽고 제한적으로 적응하게 만들 것이다

즉 앞으로의 핵심은
"엔진을 더 복잡하게 만드는 것"이 아니라,
"이미 만든 구조를 운영 판단, 기대값 해석, 자기 인식으로 연결하는 것"이다.
## 13. Current Coverage Track Update

The coverage track has now advanced through:

- `C0 baseline freeze`
- `C1 source inventory / retention matrix`

Current coverage reading:

- `coverage_gap_rows = 23`
- `archive_parquet_count = 0`
- `entry_manifest_source_count = 0`
- `inventory_state = archive_gap_dominant`

This is important because it means the near-term priority is not additional semantic tuning.
The near-term priority is `C2 coverage audit`, then `C3 archive generation hardening`, then `C4 targeted backfill`.


## 14. Coverage Track After C2

Coverage track has now advanced one more step:

- `C0 baseline freeze`
- `C1 source inventory / retention matrix`
- `C2 coverage audit report`

Latest coverage audit interpretation:

- `outside_coverage_rows = 23`
- `before_coverage_rows = 23`
- `top_gap_symbol = XAUUSD`
- `top_gap_open_date = 2026-03-27`
- `top_gap_setup_id = range_upper_reversal_sell`

So the next practical move is `C3 archive generation hardening`.
This keeps the roadmap aligned with the original direction: fix observability and retention first, then backfill, then rerun forensic, then move upward into lifecycle/expectancy work.


## 15. Coverage Track After C3

`C3 archive generation hardening` is now in place.

What changed:

- shared rollover/archive helper was extracted
- manual rollover script and runtime append path now use the same implementation
- unit coverage now includes runtime auto-rollover

Current live read:

- dry-run says `would_roll = true`
- current reason is `schema_change`

So we have crossed an important boundary:
the project is no longer only diagnosing coverage problems, it now has the code path needed to prevent future archive gaps from recurring.


## 16. Coverage Track After C6

The coverage track is now effectively closed in its internal scope.

Reference:

- [decision_log_coverage_gap_c6_close_out_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_c6_close_out_handoff_ko.md)

What this means for the larger roadmap:

- this was not an unfinished `R1~R4` item
- this was a separate `coverage / retention / archive` track discovered through `R0-B actual entry forensic`
- that track has now reached its internal close-out point

Practical interpretation:

- internal observability/retention hardening is in place
- remaining coverage gap is now best treated as `external historical source availability`
- so the roadmap can return to the main upward path: `P1 lifecycle`, `P2 expectancy`, then `P3~P5`


## 17. P-Track Canonical Docs

After C6, the canonical P-track references are:

- [profitability_operations_p_track_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p_track_detailed_reference_ko.md)
- [profitability_operations_p_track_execution_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p_track_execution_roadmap_ko.md)

Use these when the thread moves upward from coverage close-out into lifecycle / expectancy / anomaly / optimization work.
