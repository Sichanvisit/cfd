# Current Path Checkpoint Rule Tuning Takeaways From External Feedback

## 목적

이 문서는 외부 피드백 중에서
`질문을 더 잘 던지는 법` 자체는 잠시 제외하고,
**우리 구현과 rule tuning에 실제로 도움이 되는 내용만 추려서 정리한 내부 메모**다.

즉 초점은 아래다.

- 지금 바로 rule 설계에 반영할 가치가 있는가
- 지금은 보류하고 나중에 반영하는 것이 맞는가
- 프롬프트 품질에는 도움되지만 현재 구현에는 직접 영향이 적은가

---

## 한 줄 결론

외부 피드백에서 진짜 건질 만한 핵심은 5개다.

1. `action precedence`를 명시적으로 고정해야 한다
2. `active flat-profit row`를 별도 rule family로 다뤄야 한다
3. `WAIT`는 그냥 기본값이 아니라 마지막 fallback에 가깝게 다뤄야 한다
4. 추가 evidence 후보는 `1급 / 2급 / 보류`로 우선순위를 나눠야 한다
5. 일반 규칙을 만들기 전에 대표 row를 먼저 판정하는 방식이 유용하다

반대로,
답변 형식 강제나 모델별 프롬프트 변형은
외부 LLM 답 품질에는 도움되지만
현재 우리 rule 구현에 직접 필요한 건 아니다.

---

## A. 지금 바로 반영할 가치가 큰 조언

### A1. action precedence를 명시적으로 고정해야 한다

이건 프롬프트 기술이 아니라
실제 rule engine 설계 문제다.

현재 우리가 하고 있는 건 score를 계산한 뒤
어떤 action을 먼저 판정할지 정하는 일인데,
이 순서가 문서와 코드 모두에서 더 선명해야 한다.

특히 아래 축이 중요하다.

- `FULL_EXIT`
- `PARTIAL_THEN_HOLD`
- `PARTIAL_EXIT`
- `HOLD`
- `WAIT`

지금 당장 이 순서를 확정할 필요는 없지만,
적어도 “어떤 action이 다른 action보다 먼저 먹는가”는
rule spec으로 분리해 적는 게 맞다.

### 왜 중요한가

- `WAIT` 과다를 줄일 때 가장 먼저 부딪히는 것이 precedence다
- `PARTIAL_EXIT`와 `HOLD`의 애매함도 precedence 없이 정리하기 어렵다
- resolver와 hindsight bootstrap이 같은 순서를 공유해야 drift가 줄어든다

### 바로 반영 방식

- `path_checkpoint_action_resolver.py`에 precedence table 주석/상수 명시
- `path_checkpoint_dataset.py` hindsight bootstrap에도 같은 구조 반영
- 문서에도 `rule order`를 별도 섹션으로 고정

---

### A2. active flat-profit row를 별도 family로 다뤄야 한다

이건 매우 좋은 조언이다.

우리가 지금 가장 애매해하는 row가 정확히 이거다.

- `position_side != FLAT`
- `current_profit ~= 0`
- `unrealized_pnl_state = FLAT`

이 row는 그냥 “active position” 안에 뭉뚱그리면
너무 쉽게 `WAIT`로 빠진다.

즉 이건 별도 family로 보는 게 맞다.

### 왜 중요한가

- 현재 `WAIT 5 / PARTIAL_THEN_HOLD 1` 구조의 핵심 병목이 이 family다
- `FULL_EXIT`까지는 강하지 않지만 `WAIT`도 애매한 row가 여기에 몰린다
- `PARTIAL_EXIT`와 `WAIT`의 경계를 실전적으로 나누려면 이 family 분리가 필요하다

### 바로 반영 방식

- context row 또는 dataset export에 `is_active_flat_profit_row` 파생 플래그 추가
- resolver / hindsight bootstrap에서 별도 rule branch 생성
- 테스트도 이 family 전용 fixture 기준으로 추가

---

### A3. WAIT는 기본값이라기보다 마지막 fallback에 가깝게 봐야 한다

이 조언도 가치가 크다.
다만 **그대로 공격적으로 해석하면 위험하다.**

즉 “WAIT를 줄이자”가 목적이면 안 되고,
`WAIT`는 정말 다른 action이 성립하지 않을 때 남는 최후 fallback이어야 한다는 뜻으로 받아들이는 게 맞다.

### 왜 중요한가

- 지금은 bootstrap이 지나치게 보수적이라 많은 row가 `WAIT`로 모인다
- 그렇다고 무작정 `WAIT`를 줄이면 오탐이 늘어난다
- 따라서 핵심은 “WAIT 최소화”가 아니라 “WAIT로 보내기 전에 더 강한 family 판정을 먼저 시도”하는 구조다

### 바로 반영 방식

- precedence 상에서 `WAIT`를 명시적 최하단 fallback으로 둔다
- 다만 confidence / evidence 부족 시에는 계속 `WAIT`를 허용한다
- 즉 `WAIT`는 약한 label이 아니라 “판정 유보”라는 의미를 유지한다

---

### A4. additional evidence는 우선순위를 나눠서 다뤄야 한다

이것도 바로 반영할 만하다.

지금은 아래 후보들이 한데 섞여 있다.

- `mfe_since_entry`
- `mae_since_entry`
- `giveback_from_peak`
- `shock_at_profit`
- `checkpoint_type`
- `source`
- `runner_secured`
- `position_size_fraction`

이걸 그냥 “다 중요하다”로 두면
실제 rule 설계가 흐려진다.

### 현재 기준 추천 우선순위

#### 1급: 지금 바로 rule input으로 강화할 가치가 큰 것

- `checkpoint_type`
- `source`
- `runner_secured`
- `position_size_fraction`
- `giveback_from_peak`

#### 2급: 곧 넣으면 좋은 것

- `mfe_since_entry`
- `mae_since_entry`
- `shock_at_profit`

#### 3급: 지금은 보류 가능

- runner 전용 세부 label을 위한 추가 파생치
- late-trend 전용 복잡 파생치

### 왜 이렇게 보나

- `checkpoint_type`, `source`는 이미 있고 해석력도 높다
- `runner_secured`, `position_size_fraction`, `giveback_from_peak`는 `HOLD` vs `PARTIAL_THEN_HOLD` vs `PARTIAL_EXIT` 분리에 직접 연결된다
- `mfe/mae/shock`는 좋지만 지금 데이터가 얇아 초기엔 과한 복잡도를 낼 수 있다

---

### A5. 대표 row를 먼저 판정하고 일반 rule로 올라가는 방식이 유용하다

이건 매우 실무적인 조언이다.

우리는 이미 대표 사례 3개를 갖고 있고,
이 3개가 실제 병목을 잘 보여준다.

즉 다음 rule 조정은
바로 전체 일반화보다 아래 순서가 더 안전하다.

1. 대표 row를 먼저 사람이/규칙으로 판정
2. 그 판정을 만족하는 최소 rule을 작성
3. 그 rule이 다른 row까지 과도하게 흔드는지 확인

### 바로 반영 방식

- `resolver golden row test` 추가
- 대표 row 3개를 fixture로 고정
- rule 변경 시 이 3개가 어떻게 분류되는지 항상 확인

---

## B. 부분적으로만 받아들이면 좋은 조언

### B1. `WAIT 과다`를 문제로 보는 시각

이건 맞지만 절반만 맞다.

지금 병목이 `WAIT 과다`인 건 사실이지만,
더 정확히 말하면 아래 두 가지가 동시에 문제다.

- `WAIT` 과다
- `manual-exception` 과다

즉 `WAIT`만 줄여도 안 되고,
어디까지 auto-apply 해도 되는지 함께 봐야 한다.

### 받아들일 포인트

- `WAIT`를 줄일 후보 family를 찾는 건 좋다

### 조심할 포인트

- `WAIT 감소` 자체를 KPI처럼 두면 안 된다
- 우리는 여전히 precision 우선이 맞다

---

### B2. runner 전용 label을 더 세분하자는 시각

이건 방향성은 이해되지만
지금 당장 실행할 단계는 아니다.

현재 live artifact 기준:

- `runner_secured_row_count = 0`

즉 runner data가 아직 너무 얇다.

### 현재 권장 해석

- 지금은 `PARTIAL_THEN_HOLD` 안에서 흡수하는 편이 맞다
- 나중에 runner-secured row가 충분히 쌓이면
  그때 `RUNNER_HOLD` 같은 별도 label을 검토한다

즉 이 조언은 `나중 후보`로 보관하면 된다.

---

## C. 지금은 굳이 구현으로 옮길 필요가 적은 내용

### C1. 답변 형식 강제

예:

- “반드시 표로 답해 달라”
- “먼저 row 3개를 판정해 달라”
- “일반론 말고 threshold를 달라”

이건 외부 LLM에게서 더 좋은 답을 뽑는 데는 매우 좋다.
하지만 지금 우리 내부 구현 자체에 직접 반영해야 할 내용은 아니다.

즉 이건 `외부 리뷰 요청문 개선용`으로는 좋고,
`내부 rule spec` 그 자체는 아니다.

---

### C2. 모델별 프롬프트 분화

예:

- GPT용
- Claude용
- Gemini용

이건 지금 단계에선 과하다.
현재는 우리가 rule 설계 핵심만 잘 뽑아내면 된다.

---

## D. 현재 우리에게 진짜 필요한 후속 작업

외부 피드백을 우리 구현에 연결하면
다음 4개가 실제 후속 작업으로 가장 자연스럽다.

### D1. resolver / hindsight 공통 precedence spec 추가

목표:

- `management action` 판정 순서를 문서와 코드에 명시

대상:

- `backend/services/path_checkpoint_action_resolver.py`
- `backend/services/path_checkpoint_dataset.py`

핵심:

- 어느 action을 먼저 판정할지 표로 정리
- runtime과 hindsight가 완전히 같은 순서는 아니어도
  큰 구조는 공유하게 만들기

---

### D2. active flat-profit family 분리

목표:

- `position_side != FLAT`이지만 `unrealized_pnl_state = FLAT`인 row를
  별도 family로 분리

대상:

- `backend/services/path_checkpoint_context.py`
- `backend/services/path_checkpoint_dataset.py`
- `backend/services/path_checkpoint_action_resolver.py`

핵심:

- `WAIT`와 `PARTIAL_EXIT` 경계 개선
- `FULL_EXIT` 오탐은 계속 조심

---

### D3. evidence tier 문서화

목표:

- 어떤 evidence를 지금 rule에 강하게 쓰고,
  어떤 evidence는 보조로 쓰고,
  어떤 evidence는 나중으로 미룰지 고정

핵심:

- 1급: `checkpoint_type`, `source`, `runner_secured`, `position_size_fraction`, `giveback_from_peak`
- 2급: `mfe_since_entry`, `mae_since_entry`, `shock_at_profit`
- 3급: runner 세분용 추가 파생치

---

### D4. representative row 기반 golden test 추가

목표:

- rule 수정이 핵심 사례를 어떻게 바꾸는지 즉시 확인

대상:

- resolver 테스트
- dataset hindsight 테스트

핵심:

- BTCUSD flat-profit active row
- NAS100 flat-profit active row
- NAS100 open-profit continuation row

이 3개를 fixture로 고정하면
앞으로 rule tuning이 훨씬 덜 흔들린다.

---

## E. 현재 시점의 추천 판단

지금 외부 피드백을 “우리에게 필요한 것만” 추리면,
실제로 채택할 건 아래다.

### 바로 채택

- `action precedence 명시`
- `active flat-profit row 별도 family`
- `WAIT를 최하단 fallback으로 해석`
- `evidence 후보 tier 분리`
- `representative row 판정 기반 테스트`

### 보류 후 검토

- `runner 전용 label 세분`
- `더 공격적인 auto-apply 확대`

### 프롬프트용 참고만

- 답변 형식 강제
- 일반론 금지 문구 강화
- 모델별 프롬프트 버전 분리

---

## 최종 한 줄 결론

외부 피드백의 핵심 가치는
“질문을 더 세게 하라” 자체보다,
**우리 rule engine에서 precedence, active flat-profit family, evidence tier를 더 명시적으로 분리하라**
는 조언에 있다.

즉 다음 구현은
새 label을 늘리는 것보다 먼저
`WAIT가 몰리는 family를 분리하고, action 판정 순서를 고정하는 일`
이 맞다.
