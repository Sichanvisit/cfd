# 현재 구현 로드맵 네비게이션

## 1. 이 문서의 목적

지금 프로젝트는 문서가 크게 두 종류로 나뉜다.

- 전체 방향과 현재 위치를 잡는 상위 문서
- 특정 주제를 깊게 다루는 분기 문서

이 문서는 그 둘의 관계를 고정해서,
앞으로는 헷갈리지 않게 **항상 상위 문서를 기준축으로 보고, 필요한 작업만 분기 문서로 들어가는 방식**으로 운영하기 위한 안내 문서다.

즉 앞으로의 원칙은 이거다.

1. 전체 방향은 상위 문서에서 본다
2. 구체 구현은 분기 문서에서 한다
3. 작업이 끝나면 다시 상위 문서에 상태를 반영한다

---

## 2. 기준이 되는 상위 문서

### A. 전체 구조 / 연결 상태

- [current_end_to_end_system_flow_map_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_end_to_end_system_flow_map_ko.md)
- [current_unfinished_connections_and_next_steps_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_unfinished_connections_and_next_steps_ko.md)
- [current_entry_try_open_entry_zoom_map_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_entry_try_open_entry_zoom_map_ko.md)
- [current_remaining_integration_completion_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_remaining_integration_completion_detailed_plan_ko.md)
- [current_remaining_integration_completion_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_remaining_integration_completion_execution_roadmap_ko.md)

이 세 문서는 각각 아래 역할을 한다.

- 전체 흐름도: 재료 -> 상태 카드 -> 학습/관찰 -> state25 -> 실행 구조
- 미완료 연결: 지금 아직 안 닫힌 연결과 다음 작업
- 실행층 확대도: 최종 행동이 어디서 갈리는지
- 통합 상세 계획: 남은 적용/연결 항목 전체를 한 장에 모은 기준서
- 통합 실행 로드맵: 지금부터의 구현 순서를 한 장에 모은 기준서

### B. 운영 검증 / 전환 기준

- [current_ca2_guard_promotion_bounded_live_validation_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_ca2_guard_promotion_bounded_live_validation_detailed_plan_ko.md)
- [current_ca2_guard_promotion_bounded_live_validation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_ca2_guard_promotion_bounded_live_validation_execution_roadmap_ko.md)

이 두 문서는 이제 설계 문서가 아니라,
**bounded live를 언제 켤 수 있는지 판단하는 운영 검증 기준서**다.

---

## 3. 분기 문서를 쓰는 방식

특정 주제를 깊게 파야 할 때는 BC/CA 문서로 들어간다.

예:

- state25 bridge skeleton / translator / review lane
- overlap guard refinement
- runtime trace export
- continuation accuracy / execution diff
- bounded live canary

즉 분기 문서는 **특정 작업 축 하나를 닫기 위한 실행 문서**다.

### 현재 대표 분기 문서

- [current_bc11_state25_bounded_live_activation_canary_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_bc11_state25_bounded_live_activation_canary_detailed_plan_ko.md)
- [current_bc11_state25_bounded_live_activation_canary_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_bc11_state25_bounded_live_activation_canary_execution_roadmap_ko.md)

BC11은 지금 시점에서
**state25 bounded live를 실제로 어떻게 canary로 켤지**
만 따로 떼서 다루는 분기 문서다.

---

## 4. 앞으로의 기본 사용 규칙

### 규칙 1. 먼저 상위 문서를 본다

무슨 작업을 할지 정할 때는 항상 아래 순서로 확인한다.

1. [current_unfinished_connections_and_next_steps_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_unfinished_connections_and_next_steps_ko.md)
2. [current_ca2_guard_promotion_bounded_live_validation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_ca2_guard_promotion_bounded_live_validation_execution_roadmap_ko.md)

즉,

- 전체적으로 지금 어디까지 왔는가
- 지금 메인 단계가 구축인지 검증인지
- 다음 우선순위가 무엇인가

를 먼저 본다.

### 규칙 2. 그 다음 분기 문서로 들어간다

주제가 좁아지면 그때 해당 분기 문서로 들어간다.

예:

- `state25 bounded live 실제 활성화`
  -> BC11
- `guard / promotion / KPI / readiness`
  -> CA2

### 규칙 3. 작업이 끝나면 상위 문서에 상태를 환류한다

분기 문서에서 구현/검증이 끝나면,
반드시 상위 문서에도 아래 중 최소 하나를 반영한다.

- 현재 상태
- 다음 행동
- 완료 / 관찰중 / 보류

그래야 문서가 흩어지지 않는다.

---

## 5. 지금 기준으로 보는 전체 로드맵

### 5-1. 이미 많이 닫힌 것

- state-first 맥락축
  - HTF / previous box / context conflict / late chase
- continuation 학습/표식축
  - 상승 지속 / 하락 지속 후보
  - detect / propose / registry / chart overlay
- state25 bridge log-only 축
  - weight / threshold review lane
- execution 연결축
  - wrong-side guard
  - continuation promotion
  - execution diff logging

### 5-2. 지금 메인 단계

지금은 크게 보면 **관찰 / 검증 / 좁은 전환 단계**다.

즉 지금 메인 질문은:

- continuation이 실제로 맞게 읽히는가
- guard가 실제로 wrong-side를 줄이는가
- promotion이 실제로 가치 있는가
- bounded live를 켜도 되는가

### 5-3. 지금 활성 분기

- CA2
  - KPI, readiness, READY/HOLD/BLOCKED, blocker, rollback
- BC11
  - fresh 후보 재표출
  - weight bounded live canary
  - threshold bounded live canary

---

## 6. 지금 기준 권장 작업 순서

### 1단계. live 로그 / KPI 확인

- execution diff 실제 축적
- continuation accuracy 10/20/30
- guard / promotion KPI

기준 문서:

- [current_remaining_integration_completion_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_remaining_integration_completion_detailed_plan_ko.md)
- [current_ca2_guard_promotion_bounded_live_validation_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_ca2_guard_promotion_bounded_live_validation_detailed_plan_ko.md)

### 2단계. fresh bounded-live 후보 확인

- weight review / threshold review가 다시 뜨는지
- readiness artifact가 fresh한지

기준 문서:

- [current_bc11_state25_bounded_live_activation_canary_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_bc11_state25_bounded_live_activation_canary_detailed_plan_ko.md)

### 3단계. weight bounded live canary

- symbol 1개
- stage 1개
- 작은 cap

### 4단계. threshold bounded live canary

- weight canary 통과 후
- symbol별 delta 계약이 안정적일 때만

### 5단계. size는 마지막

- 현재는 보류

---

## 7. 지금처럼 문서를 쓰는 방식이 맞는 이유

앞으로는 아래처럼 운영하면 된다.

### 상위 문서

- 현재 위치를 잡는다
- 메인 우선순위를 잡는다
- 분기 문서를 어디로 들어가야 하는지 알려준다

### 분기 문서

- 좁은 작업 한 개를 상세하게 다룬다
- 구현과 검증을 닫는다

즉 지금처럼

- 상위 문서에서 “지금은 bounded live 전환 준비 단계”
- 분기 문서에서 “BC11 canary 절차”

로 가는 구조가 맞다.

---

## 8. 현재 운영 원칙

한 문장으로 정리하면:

**상위 문서는 현재 위치와 우선순위를 잡는 기준축이고, 분기 문서는 특정 작업을 깊게 수행하는 실행 문서다. 앞으로는 항상 상위 문서를 먼저 보고, 필요한 작업만 분기 문서로 들어간 뒤, 결과를 다시 상위 문서로 환류하는 방식으로 간다.**
