# Product Acceptance Chart Capture Handoff

## 목적

이 문서는 2026-04-01 기준 product acceptance 진행 상태를 한 번에 이어받기 위한 handoff 문서다.

다음 입력은 사용자가 `NAS -> XAU -> BTC` 순서로 차트 스크린샷을 전달하고,
각 차트에서 `진입해야 했던 지점`, `진입하지 말았어야 했던 지점`, `청산해야 했던 지점`, `더 버텨야 했던 지점`을 표시해 주는 흐름을 전제로 한다.

즉 다음 스레드나 다음 턴에서는 이 문서 하나를 먼저 읽고,
그 뒤에 들어오는 차트 스크린샷을 casebook evidence로 바로 연결하면 된다.

## 현재 요약

기준 baseline:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- generated_at: `2026-04-01T21:45:31`

현재 핵심 수치:

- `must_show_missing = 1`
- `must_hide_leakage = 0`
- `must_enter_candidate = 0`
- `must_block_candidate = 1`
- `must_hold_candidate = 0`
- `must_release_candidate = 10`
- `bad_exit_candidate = 10`

해석:

- `PA1` chart acceptance는 사실상 종료 상태다.
- `PA2` entry acceptance도 현재 window 기준으로는 실질 종료 상태다.
- `PA3` hold acceptance는 `must_hold = 0`으로 닫혔다.
- 현재 메인 잔여축은 `PA4 exit acceptance`다.

## 어디까지 완료됐는가

### PA1

- 공통 `state-aware display modifier` 골격 구축 완료
- `WAIT + wait_check_repeat` 계약 구축 완료
- accepted hidden suppression mirror 정리 완료
- `entry_decisions` hot payload에 chart surface logging 정리 완료
- BTC / NAS / XAU chart residue cleanup 완료

실질 상태:

- chart queue는 완료로 봐도 된다.

### PA2

- entry acceptance는 현재 baseline 기준 `must_enter = 0`
- accepted wait row / accepted hidden row가 entry 오탐으로 잡히지 않게 정리 완료

실질 상태:

- entry queue는 종료로 봐도 된다.

### PA3

- `wait/hold` acceptance 첫 target이던 `NAS SELL adverse timeout` 경계 조정 완료
- closed-trade source를 runtime path 기준으로 바로잡음
- `must_hold = 0` 확인 완료

실질 상태:

- hold queue는 종료로 봐도 된다.

### PA4

현재 active phase.

이미 반영된 핵심 축:

- `Protect Exit + wait_adverse defer` 우선순위 조정
- `meaningful giveback` early-exit bias
- `adverse weak peak` fast protect
- `countertrend topdown-only exit context` fast-exit bias
- `countertrend no-green fast cut`

실질 상태:

- fresh close row에는 새 경계가 먹고 있다.
- 다만 `must_release = 10`, `bad_exit = 10`은 아직 old backlog 영향이 남아 있다.

## PA4 잔여축 해석

현재 남은 exit residue는 대체로 아래 묶음으로 본다.

- `TopDown-only Exit Context`
- `Protect Exit + hard_guard=adverse`
- `Adverse Stop + hard_guard=adverse`
- 기타 `Exit Context` 잔여 family

중요한 점:

- 최근 fresh close에서는 `adverse_peak=weak` 신규 row가 queue로 재유입되지 않는 방향이 확인됐다.
- 즉 지금은 `새 문제 발생`보다 `예전 backlog turnover`를 보고 있는 구간에 가깝다.
- 실제 진입/청산이 적으면 PA4 숫자는 천천히만 줄어든다.

## 왜 이제 차트 스크린샷이 중요한가

지금부터는 runtime row만으로는 느리게 확인되는 구간이 있다.

특히:

- 실제 진입이 많지 않고
- 실제 청산도 자주 나오지 않으면
- PA4의 개선 효과는 closed-trade turnover가 쌓일 때까지 숫자로 늦게 보인다

그래서 다음 입력으로 들어오는 차트 스크린샷은 아래 역할을 한다.

- `should-enter / should-not-enter` evidence
- `should-hold / should-release / should-cut` evidence
- PA4 잔여 exit family를 빠르게 분류하는 casebook evidence

## 다음 입력 형식

전달 순서:

1. `NAS`
2. `XAU`
3. `BTC`

각 심볼마다 가능하면 아래를 같이 주는 것이 좋다.

- 차트 이미지 1장 이상
- 대략적인 시각 또는 캔들 구간
- 사용자가 직접 표시한 포인트
  - `여기서 진입했어야 함`
  - `여기서 진입하면 안 됨`
  - `여기서 더 버텨야 함`
  - `여기서 청산했어야 함`
  - `여기서 손절/Protect/Adverse cut이 맞음`

표시 방식은 자유롭지만 아래 정도면 충분하다.

- 화살표
- 동그라미
- `E` = entry
- `X` = exit
- `H` = hold
- `C` = cut
- 짧은 메모

## 해석 정정

이번 `NAS -> XAU -> BTC` 3장 스크린샷은
`추가 스크린샷이 더 들어올 예정인 참고 자료`가 아니라,
사용자가 직접 지정한 `진입 / 기다림 / 청산` 정답 라벨로 본다.

즉 해석 기준은 아래와 같다.

- 이 표시는 `이 지점에서 실제로 진입했어야 한다`
- 이 표시는 `이 지점에서는 기다렸어야 한다`
- 이 표시는 `이 지점에서 청산 또는 컷이 나갔어야 한다`
- 이 흐름대로 행동해야 실제 수익 쪽으로 갔다는 사용자 의도를 담은 supervisory label 이다

중요한 점:

- 현재 시스템은 실제 진입이 충분히 발생하지 않아
  `진입 -> 보유 -> 청산` 전체 사이클 검증이 느리다
- 그래서 이번 3장 스크린샷은 `future evidence`가 아니라
  곧바로 `target behavior definition`으로 사용한다
- 즉 다음 구현/조정은 이 스크린샷을 기준으로
  `언제 들어가고`, `언제 기다리고`, `언제 나가야 하는가`
  를 더 잘 맞추는 방향이어야 한다

## 스크린샷이 오면 바로 할 일

스크린샷이 들어오면 아래 순서로 처리한다.

1. 심볼별 casebook mini set 추가
2. `entry / hold / release / bad-exit` 라벨로 분류
3. 현재 PA4 잔여축과 매핑
4. 필요하면 새 `PA4 detailed -> checklist -> memo` 체인 생성
5. 다음 구현 우선순위 확정

즉 다음 입력은 단순 참고 이미지가 아니라,
곧바로 acceptance casebook과 구현 로드맵으로 연결할 evidence로 취급한다.

이번 3장은 이미 확보된 상태이므로,
다음 단계는 추가 이미지 수집이 아니라 이 3장을 `teacher label casebook`으로 쓰는 것이다.

## 먼저 읽을 문서

- [state_forecast_product_acceptance_handoff_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/state_forecast_product_acceptance_handoff_ko.md)
- [product_acceptance_reorientation_execution_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_reorientation_execution_roadmap_ko.md)
- [product_acceptance_docs_hub_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_docs_hub_ko.md)
- [product_acceptance_pa4_exit_acceptance_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_exit_acceptance_implementation_memo_ko.md)

## Round 1 Screenshot Evidence

- [product_acceptance_chart_capture_casebook_round1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_chart_capture_casebook_round1_ko.md)

## Teacher Label Split Roadmap

- [product_acceptance_chart_capture_teacher_label_split_execution_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_chart_capture_teacher_label_split_execution_roadmap_ko.md)
- [product_acceptance_pa2_teacher_label_entry_acceptance_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa2_teacher_label_entry_acceptance_detailed_reference_ko.md)
- [product_acceptance_pa3_teacher_label_wait_hold_acceptance_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_teacher_label_wait_hold_acceptance_detailed_reference_ko.md)
- [product_acceptance_pa4_teacher_label_release_cut_acceptance_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_teacher_label_release_cut_acceptance_detailed_reference_ko.md)

## 한 줄 결론

현재 상태는 `PA1 완료`, `PA2 실질 완료`, `PA3 완료`, `PA4 live turnover 확인 중`이다.

다음 입력은 `NAS -> XAU -> BTC` 순서의 차트 스크린샷이며,
각 이미지에서 `진입/청산/보유/컷` 판단 포인트를 표시해서 넘기면 된다.
