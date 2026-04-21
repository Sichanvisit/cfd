# Product Acceptance Chart Capture Teacher Label Split Execution Roadmap

## 목적

이 문서는 사용자가 제공한 `NAS -> XAU -> BTC` 차트 스크린샷 3장을
`teacher label`로 취급하고,
이를 `PA2 / PA3 / PA4`로 분해해 실제 구현축으로 연결하기 위한 실행 로드맵이다.

핵심 원칙은 단순하다.

- 스크린샷은 참고 이미지가 아니다
- 사용자가 직접 지정한 `진입 / 기다림 / 청산` 정답 샘플이다
- 따라서 다음 작업은 이 정답 샘플을 기준으로 로직을 다시 맞추는 과정이다

## 분해 원칙

이번 3장은 한 문장으로 끝나는 자료가 아니다.

동시에 아래 3가지를 말하고 있다.

1. `어디서 들어갔어야 하는가`
2. `어디서 더 기다렸어야 하는가`
3. `어디서 정리하거나 컷했어야 하는가`

그래서 작업도 아래처럼 분해한다.

## split axes

### PA2

`teacher-label entry gap`

- 시스템이 실제로 진입을 잘 하지 못하는 상황에서
- 스크린샷상 `들어가야 했던 자리`를 기준으로
- 왜 `observe / wait`에서 `entry`로 못 올라갔는지 본다

### PA3

`teacher-label wait / hold boundary`

- 스크린샷상 `기다림이 맞았던 자리`
- 즉 아직 정리하면 안 되고 hold/wait가 맞았던 자리를 기준으로
- hold가 너무 짧거나 wait가 너무 쉽게 깨지는지 본다

### PA4

`teacher-label release / cut boundary`

- 스크린샷상 `여기서 청산 또는 컷이 맞았던 자리`
- regime flip, top maturity, countertrend bounce failure 이후
- 왜 정리/컷이 늦었는지 본다

## 심볼별 요약

### NAS

- 상승 후반 chase를 줄여야 한다
- regime flip 뒤 bounce는 hold보다 release/cut 쪽이 강하다
- spike 이후 빠른 정리가 필요하다

### XAU

- 반등이 나와도 reclaim 실패면 release 쪽 bias가 더 강해야 한다
- mixed / confirm / reject 이후 늦은 정리가 반복된다
- top maturity 이후 기대 유지가 길다

### BTC

- noise / range / fake move가 가장 많다
- 관찰 신호가 행동 신호로 과소비된다
- spike fail 이후 protect/adverse cut이 더 빨라야 한다

## 현재 우선순위

우선순위는 아래처럼 잡는다.

1. `PA4`
2. `PA2`
3. `PA3`

이유:

- 현재 baseline 기준 메인 잔여축이 exit 계열에 남아 있다
- 동시에 스크린샷은 `놓친 진입`도 분명히 보여준다
- hold는 이미 PA3 수치상 많이 닫혔기 때문에, teacher-label 기준으로는 미세 조정 축으로 보는 것이 맞다

## 문서 체인

- [product_acceptance_chart_capture_handoff_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_chart_capture_handoff_ko.md)
- [product_acceptance_chart_capture_casebook_round1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_chart_capture_casebook_round1_ko.md)
- [product_acceptance_pa2_teacher_label_entry_acceptance_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa2_teacher_label_entry_acceptance_detailed_reference_ko.md)
- [product_acceptance_pa2_teacher_label_exploration_entry_layer_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa2_teacher_label_exploration_entry_layer_detailed_reference_ko.md)
- [product_acceptance_pa3_teacher_label_wait_hold_acceptance_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_teacher_label_wait_hold_acceptance_detailed_reference_ko.md)
- [product_acceptance_pa4_teacher_label_release_cut_acceptance_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_teacher_label_release_cut_acceptance_detailed_reference_ko.md)

## 한 줄 결론

다음부터는 이 3장 스크린샷을 하나의 뭉친 감상으로 보지 않고,
`PA2 진입`, `PA3 기다림`, `PA4 청산/컷` 세 축으로 쪼개서 구현 로그를 쌓는다.
