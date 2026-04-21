# P4-6F generic reason filter 상세 계획

## 목표

detector가 `manual / H1 / RSI / default / unknown` 같은
generic 표현만으로 surface되기 시작하면,
운영자는 보고도 무엇을 feedback 해야 하는지 알기 어렵다.

이번 `P4-6F`의 목적은 신호를 줄이는 것이 아니라,
`feedback 가능한 detector만 surface`되게 해서
학습 루프의 질을 지키는 것이다.

## 왜 지금 이 단계인가

`P4-6B/C/D/E`를 거치면서 detector evidence는 더 풍부해졌다.
하지만 입력 reason 자체가 generic-only면,

- evidence는 붙어도
- summary와 why-now가 운영자 체감과 멀어지고
- detector 신뢰도가 떨어질 수 있다

그래서 `P4-6F`는 evidence를 더 추가하는 단계가 아니라,
surface 가치가 낮은 generic-only 이유를 걸러내는 품질 단계다.

## generic-only 정의

### generic token 후보

- `manual`
- `h1`
- `rsi`
- `general`
- `default`
- `unknown`
- `mixed`
- `observe`

### specific token 후보

- `upper`
- `lower`
- `reject`
- `rebound`
- `reclaim`
- `box`
- `range`
- `compression`
- `wick`
- `band`
- `breakout`
- `pullback`
- `continuation`
- `follow`
- `sweep`
- `probe`
- `edge`
- `anchor`
- `touch`
- `spread`
- `trend`

## 핵심 규칙

### 1. generic-only reason

reason 토큰이 generic 후보만 있고,
specific 토큰이 하나도 없으면 `generic-only`로 본다.

예:

- `manual_h1_default`
- `observe_default`
- `unknown_general`

이 경우:

- detector surface 억제
- log-only에는 남겨도 됨

### 2. generic + specific 혼합

specific 토큰이 하나라도 있으면 surface를 허용한다.

예:

- `upper_reject_mixed_confirm`
- `upper_reject_probe_observe`

위 예시는 `mixed`, `observe`가 있더라도
`upper`, `reject`, `probe` 같은 specific 근거가 있으므로 surface 허용이다.

## 이번 단계 구현 범위

이번 단계에서 한다.

- candle/weight detector source issue에서 generic-only entry reason 억제
- scene/candle detector evidence에서 generic-only runtime check reason 숨김

이번 단계에서 하지 않는다.

- detector 자체 삭제
- reverse detector의 summary 구조 변경
- hindsight validator와 직접 연결

## 적용 위치

### 1. candle/weight detector source issue 선별

`build_manual_trade_proposal_snapshot()`에서 들어오는 issue 중
`entry_reason`이 generic-only면 source issue에서 제외한다.

즉:

- `manual_h1_default` 같은 issue는 candle detector surface 안 함
- `upper_reject_mixed_confirm`은 통과

### 2. runtime current reason evidence

scene/candle detector evidence에서
`consumer_check_reason`이 generic-only면
`현재 체크 이유:` 줄을 아예 숨긴다.

이유:

- `observe_default` 같은 줄이 evidence에 보이면 정보량이 거의 없음
- 차라리 force / box / wick / recent_3bar만 남기는 편이 낫다

## 구현 원칙

- `generic-only`만 막는다
- `generic + specific 혼합`은 살린다
- detector signal을 꺼버리는 게 아니라
  surface 설명을 더 읽을 만하게 만든다

## 건드릴 파일

- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)
- [test_improvement_log_only_detector_p46f.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_improvement_log_only_detector_p46f.py)

## 완료 조건

- generic-only entry reason은 candle detector로 surface되지 않는다
- `upper_reject_mixed_confirm` 같은 혼합 reason은 계속 surface된다
- generic-only `consumer_check_reason`은 evidence line에서 숨겨진다
- 거래 로직은 바뀌지 않는다

## 다음 단계

- `P4-6I` confidence / explainability snapshot / cooldown
- 그 다음 `P4-6G` hindsight validator + fast promotion

즉 `P4-6F`는 detector를 더 똑똑하게 만드는 단계라기보다,
detector가 운영자에게 덜 성가시고 더 믿을 만하게 보이도록 정리하는 단계다.
