# BC6 State25 Threshold Log-Only Translator 상세 계획
## 목표

BC6의 목적은 state-first context를 state25의 threshold 손잡이에 **log-only harden translator**로 번역하는 것이다.

핵심 원칙은 이렇다.

- 새 decision core를 만들지 않는다.
- 방향을 강제로 뒤집지 않는다.
- v1은 `HARDEN only`로 시작한다.
- threshold 보정은 먼저 runtime trace와 decision counterfactual로 검증한다.

즉 BC6는 "바로 진입을 막는 장치"가 아니라, **지금 맥락이면 얼마나 더 까다롭게 봤어야 했는지**를 runtime에 기록하는 단계다.

## 왜 BC6가 필요한가

지금까지의 흐름은 아래까지 왔다.

- ST1~ST4
  - HTF / previous box / conflict / late chase를 runtime state에 올림
- ST5~ST9
  - detector / notifier / propose/hindsight가 큰 그림을 읽음
- BC1~BC5
  - state25 context bridge skeleton, weight translator, runtime export, review lane, overlap guard refinement

문제는 여기서 아직 남아 있다.

- 설명층은 "이 장면은 불편하다"고 말할 수 있다.
- state25 weight도 일부는 보정 후보가 생긴다.
- 하지만 "이 장면이면 진입 문턱을 더 높였어야 했다"는 threshold 보정은 아직 약하다.

그래서 BC6는 아래 질문에 답하는 단계다.

- HTF 역행이면 threshold를 얼마나 더 높였어야 했는가
- 직전 박스와 상위 추세가 모두 불편하면 threshold를 얼마나 보수화했어야 했는가
- 늦은 추격 위험이 높을 때 threshold가 실제로 decision을 바꿨는가

## 입력으로 쓰는 context

BC6는 interpreted context를 중심으로 쓴다.

- `context_conflict_state`
- `context_conflict_intensity`
- `htf_alignment_state`
- `htf_against_severity`
- `previous_box_break_state`
- `late_chase_risk_state`
- `entry_stage`

raw context는 보정 강도에만 제한적으로 쓴다.

- `trend_*_age_seconds`
- `previous_box_age_seconds`
- `threshold_base_points`
- `score_reference`

원칙은 이렇다.

- interpreted = 보정 방향
- raw = 보정 강도와 freshness

## threshold translator 규칙

BC6는 `HARDEN only`다.

대표 harden 입력은 아래다.

- `AGAINST_HTF`
- `AGAINST_PREV_BOX_AND_HTF`
- `late_chase_risk_state = HIGH`

예상 작동 방향:

- `AGAINST_HTF`
  - threshold를 소폭 상향
- `AGAINST_PREV_BOX_AND_HTF`
  - threshold를 더 강하게 상향
- `LATE_CHASE_RISK HIGH`
  - 방향 보정보다 timing/risk 쪽 harden

## stage multiplier와 cap

entry stage에 따라 동일 context라도 harden 강도를 다르게 본다.

- `aggressive`
  - multiplier 작게
  - cap도 낮게
- `balanced`
  - 기본값
- `conservative`
  - multiplier 크게
  - cap도 조금 높게

이때 중요한 점은 multiplier만 두지 않고 cap도 같이 둔다는 것이다.

즉:

- aggressive는 과도한 보수화 방지
- conservative는 더 엄격한 harden 허용

## freshness와 component activation

threshold translator도 freshness를 그대로 따른다.

- `FRESH`
  - 100% 반영
- `AGING`
  - 부분 반영
- `STALE`
  - threshold effective는 0, trace만 남김

component별 activation도 같이 적용한다.

- `htf`
- `previous_box`
- `late_chase`
- `share`

BC6에서 share는 authority가 아니라 booster이므로 threshold 단독 권한은 주지 않는다.

## requested / effective / suppressed

BC6 trace는 세 층을 분리한다.

- `threshold_adjustment_requested`
  - 이 맥락이면 얼마나 harden하려 했는가
- `threshold_adjustment_effective`
  - freshness / cap / overlap guard를 거친 뒤 실제 유효한 값
- `threshold_adjustment_suppressed`
  - 왜 반영이 0이 되었는가

추가 메타:

- `threshold_delta_direction`
  - v1은 `HARDEN` only
- `threshold_delta_reason_keys`
  - 어떤 context가 harden 이유였는가
- `threshold_stage_multiplier`
- `threshold_stage_cap_points`
- `threshold_source_field`

## decision counterfactual

BC6에서 가장 중요한 검증 포인트는 decision counterfactual이다.

v1에서는 먼저 decision 단계만 본다.

- `without_bridge_decision`
- `with_bridge_decision`
- `bridge_changed_decision`
- `score_reference_value`
- `threshold_base_points`
- `threshold_candidate_points`

즉 먼저 보는 것은:

- "이 threshold harden이 실제로 ENTER를 SKIP으로 바꿨는가"

성과까지 단정하는 outcome counterfactual은 이후 hindsight가 더 쌓인 뒤 단계다.

## BC6에서 아직 하지 않는 것

- threshold live apply
- RELAX 방향 보정
- threshold 전용 detector review lane
- threshold 전용 `/propose` 독립 섹션
- outcome counterfactual 확정 판정

즉 BC6는 **runtime trace와 log-only decision counterfactual**까지를 닫는 단계다.

## 완료 기준

- `state25_context_bridge.py`가 threshold requested/effective/suppressed를 계산한다.
- runtime/detail/slim/hot payload에 threshold flat field가 실린다.
- decision counterfactual이 populated된다.
- 테스트에서 harden과 decision changed 케이스가 검증된다.
- 운영 설명 문서에서 `/detect -> /propose`와 BC6의 현재 노출 위치가 정리된다.
