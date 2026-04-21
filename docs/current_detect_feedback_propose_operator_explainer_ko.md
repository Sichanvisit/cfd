# `/detect` / `/detect_feedback` / `/propose` 운영 설명서
## 목적

이 문서는 체크방에서 쓰는 세 명령이 각각 무엇을 보여주는지, 어떤 순서로 보면 좋은지, 지금 시스템에서 어디까지 자동으로 연결되어 있는지를 운영자 관점에서 설명한다.

중요한 전제는 이렇다.

- 이 세 명령은 바로 라이브 규칙을 바꾸는 명령이 아니다.
- 먼저 관찰하고, 피드백을 남기고, review backlog로 올리는 루프다.
- 지금 단계의 핵심은 "왜 이상해 보였는지"를 모으고 비교 가능한 형태로 쌓는 것이다.

## 한 줄 요약

- `/detect`
  - 지금 detector가 "이상하거나 review 가치가 있다"고 보는 관찰 항목을 보여준다.
- `/detect_feedback`
  - `/detect`에서 본 항목이 맞았는지, 과민했는지, 놓쳤는지 채점한다.
- `/propose`
  - 최근 거래와 detector/feedback 결과를 바탕으로 review backlog 후보를 정리해 보여준다.

## 가장 권장하는 운영 순서

1. `/detect`
2. 필요한 항목에 `/detect_feedback D번호 ...`
3. `/propose`

이 순서가 좋은 이유는 `/propose`가 최신 detector 관찰과 feedback 흐름을 묶어서 보여주기 때문이다.

## `/detect`에서 무엇이 보이나

`/detect`는 detector가 surface한 최신 관찰 항목을 보고서 topic에 올린다.

보통 아래 묶음이 나온다.

- `scene-aware detector`
  - HTF/직전 박스/맥락 충돌이 붙은 장면
  - semantic observe cluster
  - semantic continuation gap
  - 예: `NAS100 상승 지속 누락 가능성 관찰`
- `candle/weight detector`
  - 캔들/박스/방향 해석 mismatch
  - state25 weight review 후보
- `reverse pattern detector`
  - missed reverse / shock 반복

각 항목에서 주로 보는 값은 이렇다.

- `D번호`
  - 이후 `/detect_feedback` 대상 번호다.
- `이유`
  - 왜 detector가 이 장면을 이상하다고 봤는지 설명한다.
- `분류`
  - 결과 오판인지, 결과 미확정인지, 설명 부족인지 같은 관찰 타입이다.
- `사후 판정`
  - hindsight 기준으로 이미 강하게 확인된 문제인지 본다.
- `HTF`, `직전 박스`, `늦은 추격`, `맥락`
  - state-first context가 붙은 경우 큰 그림을 같이 읽을 수 있다.

### 현재 `/detect`에서 실제로 보일 수 있는 대표 항목

- `BTCUSD 상하단 방향 오판 가능성 관찰`
- `BTCUSD baseline no-action observe cluster 관찰`
- `NAS100 상승 지속 누락 가능성 관찰`
- `XAUUSD missed reverse / shock 패턴 관찰`
- `BTCUSD missed reverse / shock 패턴 관찰`
- `state25 context bridge weight review 후보`
  - BC4 lane이 살아 있는 경우 candle/weight detector에 뜬다.

## `/detect_feedback`는 왜 중요한가

`/detect_feedback`은 detector를 채점하는 단계다.

예시 형식:

```text
/detect_feedback D1 맞았음
/detect_feedback D2 과민했음
/detect_feedback D3 놓쳤음
/detect_feedback D4 맞았음 HTF는 맞는데 timing은 아쉬웠음
```

이 피드백은 아래로 이어진다.

- detector confusion 누적
- feedback-aware priority 조정
- `/propose` backlog 우선순위 반영

쉽게 말하면:

- `/detect`는 시스템의 주장
- `/detect_feedback`은 운영자의 채점

이다.

## `/propose`에서 무엇이 보이나

`/propose`는 최근 마감 거래, detector 결과, feedback 누적을 묶어서 review backlog를 정리한다.

지금 구조에서 보통 아래 섹션이 나온다.

- `semantic observe cluster 후보`
  - baseline no-action / observe가 반복되는 군집
- `semantic gate review 후보`
  - `semantic_shadow_trace_quality`, `energy_soft_block`, `execution_soft_blocked` 같은 gate
- `문제 패턴`
  - 최근 마감 거래에서 반복 손실/과민이 나타난 패턴
- `state25 context bridge weight review 후보`
  - BC4가 surface한 경우 state25 weight-only review packet이 들어온다.

각 섹션은 보통 아래 의미를 가진다.

- `semantic observe cluster 후보`
  - semantic이 반복해서 observe/no-action으로 머무르는 장면
- `semantic gate review 후보`
  - semantic을 막는 문턱이 무엇인지 review하는 후보
- `문제 패턴`
  - 실제 거래 패턴 관점의 review 대상
- `state25 context bridge weight review 후보`
  - 큰 그림 context를 state25 weight에 log-only로 번역한 결과를 review backlog로 보는 후보

## `/detect -> /propose`를 같이 보면 무엇이 연결되나

이 두 명령을 연속으로 보면 아래 흐름이 보인다.

1. `/detect`
  - 지금 detector가 surface한 장면을 본다.
2. `/propose`
  - 그 장면이 review backlog에서 어떤 후보로 올라오는지 본다.

대표적인 연결 예시는 이렇다.

- `/detect`에서 `NAS100 상승 지속 누락 가능성 관찰`
  - `/propose`에서 `semantic observe cluster 후보`로 이어질 수 있다.
- `/detect`에서 semantic unavailable / no-action cluster 관찰
  - `/propose`에서 `semantic gate review 후보`로 이어진다.
- `/detect`에서 candle/weight detector의 bridge review 후보 관찰
  - `/propose`에서 `state25 context bridge weight review 후보`로 이어질 수 있다.

즉 `/detect`는 "무슨 장면이 문제로 보이는가"이고, `/propose`는 "그래서 무엇을 review backlog에 올릴 것인가"다.

## state-first context와 state25 bridge는 지금 어디까지 보이나

현재는 아래 연결이 이미 되어 있다.

- runtime state
- detector
- notifier
- propose / hindsight
- state25 context bridge runtime trace

그래서 detector 메시지에서 이미 아래 큰 그림을 읽을 수 있다.

- `HTF`
- `직전 박스`
- `맥락 충돌`
- `늦은 추격 위험`

또 state25 bridge는 현재 아래 단계까지 와 있다.

- `BC2`
  - weight-only translator
- `BC3`
  - runtime trace export
- `BC4`
  - weight-only review lane
- `BC5`
  - overlap guard refinement
- `BC6`
  - threshold log-only translator

## BC6는 `/detect`와 `/propose`에서 어떻게 보이나

여기서 중요한 점이 하나 있다.

BC6 threshold translator는 지금 **runtime trace와 log-only counterfactual** 중심이다.

즉 현재는 아래가 맞다.

- runtime row에는 BC6 threshold trace가 실린다.
- flat summary field도 같이 실린다.
- decision counterfactual도 남는다.

하지만 아직은 아래 단계가 아니다.

- threshold 전용 detector review lane
- threshold 전용 `/propose` 섹션

그래서 지금 `/detect -> /propose`를 봤을 때 바로 독립된 `threshold review 후보`가 항상 나오는 것은 아니다.

현재 보이는 것은 주로:

- state25 bridge의 weight review 후보
- 그리고 BC6 threshold는 그 뒤 런타임 trace와 후속 review 준비 데이터로 쌓이는 상태

즉 BC6는 "이미 계산되고 기록되지만, 아직 독립 review lane으로는 크게 surface되지 않은 단계"라고 보면 맞다.

## 언제 무엇을 보면 좋은가

### 1. 차트가 이상하게 보일 때

1. `/detect`
2. HTF / 직전 박스 / semantic cluster / reverse detector 확인
3. 필요하면 `/detect_feedback`
4. `/propose`로 backlog 후보 확인

### 2. semantic이 계속 observe/no-action일 때

1. `/detect`
2. semantic observe cluster 항목 확인
3. `/propose`
4. semantic gate review 후보 확인

### 3. state25가 큰 그림과 안 맞게 점수를 내는 것 같을 때

1. `/detect`
2. candle/weight detector와 context bundle 문장 확인
3. `/propose`
4. `state25 context bridge weight review 후보`가 올라오는지 확인

### 4. threshold 보정이 실제로 영향 있는지 보고 싶을 때

현재는 `/detect`나 `/propose`의 독립 섹션보다 runtime trace 쪽이 더 직접적이다.

즉 BC6는 지금

- detector main section보다는
- runtime/detail trace와 이후 review lane 준비

에 더 가깝다.

## 운영자가 기억하면 되는 핵심

- `/detect`
  - 지금 뭐가 이상한지 본다.
- `/detect_feedback`
  - 그 판단이 맞았는지 채점한다.
- `/propose`
  - 그래서 무엇을 review backlog에 올릴지 본다.

그리고 현재 state-first / state25 bridge 흐름은 이렇게 이해하면 된다.

- weight bridge는 review lane까지 올라오기 시작했다.
- threshold bridge는 log-only trace까지 올라왔다.
- size bridge는 아직 뒤 단계다.

한 줄로 정리하면:

**지금 `/detect -> /propose`는 "문제 장면 관찰 -> review backlog 정리" 루프이고, state25 bridge는 weight는 review까지, threshold는 trace까지 올라온 상태다.**
