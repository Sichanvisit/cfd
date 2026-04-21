# BC4 State25 Weight-Only Log-Only Review Lane 상세 계획
## 목표

`state25_candidate_context_bridge_v1`가 만든 weight-only translator 결과를
단순 runtime trace에만 남기지 않고,
`detector -> /propose -> state25 weight review packet`까지 이어지는
bounded review lane으로 surface한다.


## 현재 상태

- BC1: bridge skeleton 완료
- BC2: weight-only translator 완료
- BC3: runtime/detail/slim/hot payload export 완료

즉 지금은 bridge가 내부적으로
- requested weight
- effective weight
- suppressed weight
- failure / guard
- trace reason codes
를 계산하고 runtime row에 싣고 있다.

하지만 아직 review backlog에서는
이 결과를 별도 weight review 후보로 직접 읽지 못한다.


## 왜 BC4가 필요한가

지금 상태는
- detector/notifier/propose가 큰 그림 context는 설명할 수 있지만
- state25 bridge가 만든 weight-only 조정 후보는
  운영자가 review backlog에서 바로 비교하기 어렵다.

BC4의 목적은
“bridge가 무엇을 조정하려 했는지”를
state25 weight review packet으로 올려서
운영자가 detector와 `/propose`에서 같은 후보를 보게 만드는 것이다.


## 구현 범위

### 1. review packet helper
- 파일: `backend/services/state25_weight_patch_review.py`
- 추가:
  - context bridge payload에서 requested/effective/suppressed weight를 읽는 helper
  - bridge trace를 evidence snapshot에 싣는 review candidate builder

### 2. detector lane
- 파일: `backend/services/improvement_log_only_detector.py`
- 추가:
  - runtime row의 `state25_candidate_context_bridge_v1`를 읽어
    candle/weight detector lane에
    `state25 context bridge weight review 후보`를 surface
  - `weight_patch_preview`에 bridge 기반 review packet 연결

### 3. propose lane
- 파일: `backend/services/trade_feedback_runtime.py`
- 추가:
  - 최신 detector refs에서 BC4 review packet을 추출
  - `/propose` report에 별도 section으로 표시
  - proposal envelope evidence snapshot에 count / registry keys 추가


## 운영 원칙

- BC4는 `log_only review lane`이다.
- 실제 apply를 바로 열지 않는다.
- requested/effective/suppressed를 분리해 보여준다.
- `late_chase`는 여전히 weight보다 threshold/size 우선 원칙을 유지한다.


## 완료 기준

- detector에서 bridge 기반 weight review row가 surface된다.
- `/propose` report에 BC4 review section이 보인다.
- review packet evidence snapshot에
  context / failure / guard / trace reason codes가 남는다.
