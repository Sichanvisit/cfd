# DB3. trade_feedback_runtime Direct Binding 상세 계획

## 목표

`/propose`가 detector에서 올라온 항목을 같은 `registry_key` 흐름으로 읽고,
feedback-aware promotion 정책도 중앙 레지스트리 기준으로 설명할 수 있게 만든다.

이번 단계의 목적은 proposal 문장을 획일화하는 것이 아니라,

- detector가 본 근거
- proposal runtime이 참고한 승격 정책
- 이후 review/apply로 이어질 downstream target

을 같은 payload 안에서 분리해 싣게 만드는 것이다.

## 왜 지금 이 단계인가

- `DB1`에서 detector row가 `registry_key / evidence_registry_keys / target_registry_keys`를 이미 싣고 있다.
- `DB2`에서 state25 weight review가 중앙 registry label을 직접 읽기 시작했다.
- 이제 `/propose`만 detector와 review 사이에서 아직 옛 언어를 쓰면,
  입력은 새 말이고 출력은 옛 말인 상태가 남는다.

즉 `DB3`는 새 기능 추가가 아니라,
이미 연결된 detector -> feedback -> propose 루프를 같은 key 언어로 수렴시키는 단계다.

## 이번 단계의 바인딩 원칙

### 1. proposal runtime의 primary registry는 promotion policy다

feedback-aware promotion row의 `registry_key`는 proposal runtime이 실제로 참고한 승격 정책을 대표한다.

첫 대표 key는 아래를 사용한다.

- `promotion:hindsight_status`

이 key는 fast promotion 여부와 일반 promotion priority를 가르는 가장 설명적인 축이기 때문이다.

### 2. detector evidence는 `evidence_registry_keys`로 유지한다

detector가 이미 가지고 있던

- `misread:*`
- `forecast:*`
- 기타 detector evidence key

는 proposal runtime에서도 그대로 evidence로 이어받는다.

즉 proposal은 새 evidence를 발명하지 않고,
detector가 본 근거를 같은 key로 이어받아 요약한다.

### 3. proposal policy target과 downstream target을 분리한다

proposal runtime이 지금 당장 참고하는 조절 축은 `feedback promotion policy`다.

따라서 row의 `target_registry_keys`는 아래 promotion policy key를 사용한다.

- `promotion:hindsight_status`
- `promotion:fast_promotion_min_feedback`
- `promotion:fast_promotion_min_positive_ratio`
- `promotion:fast_promotion_min_trade_days`
- `promotion:fast_promotion_min_misread_confidence`

반면 detector가 이미 제안 후보로 들고 있던 weight target은 별도로 보존한다.

- `downstream_target_registry_keys`

이렇게 분리하면

- 지금 무엇으로 승격을 판단했는지
- 나중에 무엇을 조절할 후보였는지

를 섞지 않게 된다.

## 주요 필드 계약

feedback-aware promotion row는 가능하면 아래 필드를 갖는다.

- `registry_key`
- `registry_label_ko`
- `registry_binding_mode`
- `registry_binding_version`
- `registry_binding_ready`
- `evidence_registry_keys`
- `target_registry_keys`
- `evidence_bindings`
- `target_bindings`
- `detector_registry_key`
- `detector_registry_label_ko`
- `downstream_target_registry_keys`
- `downstream_target_bindings`

문제 패턴 row는 자체 `registry_key`를 억지로 갖지 않는다.
대신 top match 기준으로 아래를 싣는다.

- `feedback_priority_registry_key`
- `feedback_priority_registry_label_ko`
- `feedback_priority_binding_mode`
- `feedback_priority_evidence_registry_keys`
- `feedback_priority_target_registry_keys`

즉 문제 패턴 row는 “자기 own key”가 아니라
“어떤 feedback-aware promotion과 연결되었는가”를 표시한다.

## 구현 범위

대상 파일:

- [trade_feedback_runtime.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_feedback_runtime.py)

이번 단계에서 한다:

- resolver import
- promotion policy key 상수 선언
- feedback promotion row direct binding helper 추가
- proposal payload/evidence snapshot에 binding summary 추가
- surfaced problem pattern에 feedback priority binding 정보 추가

이번 단계에서 하지 않는다:

- detector scoring 변경
- proposal 우선순위 계산식 변경
- apply executor 변경
- report 문장 강제 통일

## 완료 조건

- `feedback_promotion_rows`가 direct binding 필드를 가진다
- `surfaced_problem_patterns`가 top feedback match 기준 binding 정보를 가진다
- `proposal_envelope.evidence_snapshot`에 binding summary가 들어간다
- audit에서 `feedback_direct_binding = true`가 된다

## 기대 효과

- detector에서 본 항목과 `/propose`에서 검토하는 항목이 같은 key로 이어진다
- fast promotion이 어떤 정책 축을 근거로 올라왔는지 payload에서 바로 읽을 수 있다
- 이후 `DB4 forecast/report`에서도 detector/proposal과 같은 registry_key 문법으로 확장하기 쉬워진다
