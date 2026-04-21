# Product Acceptance Chart Capture Casebook Round 1

## 입력

사용자 제공 차트 스크린샷 3장:

1. `NAS100`
2. `XAUUSD`
3. `BTCUSD`

이번 문서는 스크린샷 자체를 정밀 시간축 데이터로 재구성한 문서가 아니라,
사용자가 직접 표시한 포인트를 `acceptance casebook evidence`이자
`teacher label`로 해석한 1차 정리 문서다.

즉 목적은 아래 두 가지다.

- 다음 구현축을 빠르게 좁히기
- 나중에 runtime row / closed trade와 대조할 기준을 미리 고정하기

추가 해석:

- 이번 3장은 `다음에도 계속 이어서 받을 참고 스크린샷`이 아니다
- 사용자가 현재 시스템이 실제로 진입을 잘 하지 않는 상황에서
  `진입했어야 할 자리`, `기다렸어야 할 자리`, `청산했어야 할 자리`
  를 직접 표시해 준 기준 자료다
- 따라서 이 문서의 표기는 단순 관찰 메모가 아니라
  `수익이 나도록 맞춰야 하는 행동 정답 샘플`로 사용한다

## 공통 해석

세 심볼에 공통으로 보이는 패턴은 아래다.

1. 상승 구간 후반의 `늦은 추격 진입`이 많다.
2. 상승에서 하락으로 regime이 바뀌는 구간에서 `release / cut`이 늦다.
3. 하락 red zone 안 countertrend bounce에서 `재진입` 또는 `hold 지속`이 과하다.
4. 추세가 명확하지 않은 noise/range 구간에서 `관찰 신호`가 너무 많이 `행동 신호`처럼 소비된다.

현재 PA4와 연결하면,
이번 스크린샷은 단순 entry 문제가 아니라
`trend maturity`, `regime flip`, `countertrend bounce`, `late protect/cut`
축을 더 강하게 다뤄야 한다는 evidence로 보는 것이 맞다.

## NAS100

### 1차 읽기

- 좌측과 중단의 green zone에서는 추세 상승이 비교적 분명하다.
- 상단 고점대와 green/red 경계 부근에서 과도한 action 흔적이 몰려 있다.
- red zone 진입 후에는 bounce가 여러 번 나오지만 결국 lower-high / lower-low로 계속 눌린다.
- 우측 큰 수직 spike 이후 바로 밀리는 구간은 `추격`보다 `release / no-chase / fast cut` evidence에 가깝다.

### acceptance 해석

- top maturity 부근의 추가 long/late chase는 줄여야 한다.
- red zone 진입 뒤 countertrend bounce는 `hold 근거`보다 `정리 근거`로 읽는 쪽이 더 맞다.
- 특히 큰 spike 이후 바로 무너지는 구간은 `protect exit / adverse release` 쪽으로 더 빨리 기울어야 한다.

### 구현 메모

- `PA4 countertrend topdown-only exit context`
- `PA4 weak-peak adverse fast protect`
- `PA4 no-green countertrend fast cut`

이번 NAS 스크린샷은 위 3축이 방향상 맞다는 추가 시각 증거로 사용한다.

## XAUUSD

### 1차 읽기

- 좌측 green zone은 추세상승과 눌림목이 반복되는 구조다.
- 상단 과열 구간에서 추격/재진입 흔적이 많고, 이후 red zone 진입 뒤에는 하락 추세가 더 선명하다.
- red zone 안 반등들이 몇 차례 나오지만 상단 reclaim이 실패하고 다시 눌린다.
- 우하단 최종 하락 구간은 `계속 버텨야 하는 장면`보다 `이미 정리됐어야 하는 장면`으로 보인다.

### acceptance 해석

- `upper reject / mixed confirm / forecast guard` 계열에서 늦은 기대 유지가 있었던 것으로 읽힌다.
- red zone bounce는 `새 진입 기회`보다 `release` 또는 `no-reentry` 근거가 강하다.
- 즉 XAU는 `반등이 나왔으니 더 버틴다`보다 `반등도 reclaim 실패면 정리` 쪽 bias가 더 필요하다.

### 구현 메모

- `PA4 meaningful giveback early exit bias`
- `PA4 exit-context release acceleration`
- 향후 스크린샷 2차분이 오면 `upper reject mixed / confirm` exit family와 직접 매핑 필요

## BTCUSD

### 1차 읽기

- NAS/XAU보다 훨씬 더 `noise / range / fake move`가 많다.
- 좌측과 중앙의 횡보 구간에서 작은 흔적이 매우 많고, 관찰 포인트 대비 action 밀도가 높다.
- 우측 상단 spike는 강한 추세 전환 신호라기보다 `reject 이후 급락` 장면에 가깝다.
- 이후 하단으로 눌리는 구간은 추가 hold보다 `빠른 release / cut` 쪽 evidence가 강하다.

### acceptance 해석

- BTC는 세 심볼 중 `관찰 신호가 행동 신호로 과소비되는 문제`가 가장 강하게 보인다.
- range/noise 구간에서는 더 많이 숨기거나 wait로 남겨야 한다.
- spike fail 이후엔 특히 `protect exit / adverse stop`이 늦지 않아야 한다.

### 구현 메모

- `PA4 Protect Exit + hard_guard=adverse`
- `PA4 Adverse Stop + hard_guard=adverse`
- 필요하면 이후 `range/noise observe suppression`을 별도 casebook 축으로 분리

## Round 1 결론

이번 1차 스크린샷 묶음으로 고정할 핵심은 아래다.

1. `상승 후반 추격 진입`은 세 심볼 공통으로 줄여야 한다.
2. `regime flip 이후 bounce`는 세 심볼 공통으로 hold보다 release/cut 근거가 더 강하다.
3. `BTC`는 noise/range 구간에서 행동 과밀도가 특히 크다.
4. `NAS/XAU`는 top maturity 이후 늦은 release가 반복되는 그림이 더 선명하다.

즉 다음 PA4 해석은
`더 기다릴 이유 찾기`보다 `왜 여기서 더 빨리 정리해야 했는가`
쪽이 더 중요하다고 본다.

그리고 이번 3장은 PA4만의 자료가 아니다.

- `PA2`: 어디서 실제 진입이 나와야 했는가
- `PA3`: 어디서 기다림이 맞았는가
- `PA4`: 어디서 release/cut가 맞았는가

를 동시에 보여주는 `행동 정답 케이스`로 취급한다.

## 다음 사용법

이 문서는 현재 확보된 3장을 기준 casebook으로 고정한다.

즉 다음 단계는
`추가 스크린샷 수집`이 아니라
이 3장을 기준으로 실제 로직이

- entry를 너무 늦게 내는지
- wait를 잘못 길게 잡는지
- exit/cut가 늦는지

를 맞춰 가는 쪽이다.

## 연결 문서

- [product_acceptance_chart_capture_handoff_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_chart_capture_handoff_ko.md)
- [product_acceptance_pa4_exit_acceptance_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_exit_acceptance_implementation_memo_ko.md)
- [product_acceptance_docs_hub_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_docs_hub_ko.md)
