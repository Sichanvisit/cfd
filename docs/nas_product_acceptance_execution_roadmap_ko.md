# NAS Product Acceptance Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `NAS100`을 첫 product acceptance 심볼로 고정하고,
사용자 스크린샷 기준으로

- 어떤 표기를 먼저 맞출지
- 어떤 owner를 어떤 순서로 건드릴지
- 어디까지 맞춘 뒤 entry/wait/exit로 넘어갈지

를 실행 단계로 쪼갠 로드맵이다.

상세 기준 문서는 아래를 본다.

- [nas_product_acceptance_casebook_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\nas_product_acceptance_casebook_reference_ko.md)

상위 제품 acceptance 문서는 아래를 본다.

- [product_acceptance_reorientation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_detailed_reference_ko.md)
- [product_acceptance_reorientation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_execution_roadmap_ko.md)

현재 첫 실전 샘플과 조정 후보 메모는 아래를 같이 본다.

- [nas_product_acceptance_first_capture_casebook_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\nas_product_acceptance_first_capture_casebook_ko.md)
- [nas_product_acceptance_initial_adjustment_targets_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\nas_product_acceptance_initial_adjustment_targets_ko.md)
- [nas_product_acceptance_first_adjustment_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\nas_product_acceptance_first_adjustment_implementation_memo_ko.md)
- [nas_product_acceptance_second_adjustment_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\nas_product_acceptance_second_adjustment_implementation_memo_ko.md)

## 2. 전체 흐름

```text
NAS0. screenshot baseline freeze
-> NAS1. screenshot casebook labeling
-> NAS2. display importance remap
-> NAS3. chart acceptance replay review
-> NAS4. entry / wait tie-in
-> NAS5. exit sanity review
-> NAS6. NAS close-out and expansion decision
```

## 3. 현재 시작점

현재 시작점은 아래처럼 본다.

- 사용자 NAS screenshot 1장 확보
- 흰색 동그라미 다수 표시 완료
- 해석 초안:
  - 박스 하단 반전/회복 시작점 = `3`
  - 중간 눌림 후 재상승 = `2`
  - 작은 continuation 되돌림 = `1`

즉 지금은 `NAS0`와 `NAS1`의 입력이 이미 생긴 상태다.

## 4. NAS0. Screenshot Baseline Freeze

### 목표

지금 NAS가 어떻게 보이는지와
사용자가 무엇을 원하는지의 기준면을 먼저 고정한다.

### 할 일

1. 현재 NAS screenshot을 baseline case로 등록한다.
2. 가능하면 이후 screenshot에는 아래 라벨을 같이 붙인다.
- `3`
- `2`
- `1`
- `W`
- `X`
3. screenshot 시점에 대응되는 row / session context가 있으면 같이 저장한다.

### 산출물

- NAS must-show / must-hide 기초 casebook
- NAS current vs desired baseline 메모

### 완료 기준

- “지금 무엇이 문제인지”가 막연한 체감이 아니라
  screenshot case로 고정된다.

## 5. NAS1. Screenshot Casebook Labeling

### 목표

동그라미만 있는 screenshot을
실제 조정 가능한 label 체계로 바꾼다.

### 라벨 체계

- `3` = 강한 구조 반전/회복 시작
- `2` = 중간 눌림 후 재가속
- `1` = 작은 continuation
- `W` = WAIT
- `X` = 뜨면 안 됨

### 할 일

1. screenshot에서 핵심 spot을 위 라벨로 재기록한다.
2. 각 spot을 대략 아래로 묶는다.
- lower recovery start
- clean confirm pullback
- continuation pullback
- noisy / should-hide
3. label별 대표 scene을 3~5개씩 뽑는다.

### 완료 기준

- NAS acceptance를 `3/2/1/W/X`로 말할 수 있다.

## 6. NAS2. Display Importance Remap

### 목표

기존 `0.70 / 0.80 / 0.90` ladder는 유지하되,
NAS에서만 `체크 개수 = 구조 중요도`에 더 가깝게 보이도록 만든다.

### 주 owner

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_symbol_override_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_symbol_override_policy.py)

### 먼저 건드릴 것

1. `consumer_check_state.py`
- NAS lower recovery 시작점 uplift
- NAS clean confirm 재상승 2-check 안정화
- NAS continuation 약화
- WAIT와 directional display 분리 강화

2. `chart_symbol_override_policy.py`
- `nas_clean_confirm_probe` 범위 재점검
- NAS-specific relief / scene allow 확장 필요성 점검

### 나중에만 건드릴 것

- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)

이유:

- painter는 translation layer라 upstream이 맞아야 한다.
- NAS 첫 pass는 painter보다 consumer/display 쪽이 먼저다.

### 완료 기준

- NAS chart에서 3/2/1 분포가 사용자의 screenshot 의도에 가까워진다.

## 7. NAS3. Chart Acceptance Replay Review

### 목표

조정 후 chart가 실제로 더 나아졌는지
다시 screenshot / recent chart 기준으로 확인한다.

### 할 일

1. NAS chart recent snapshot을 다시 본다.
2. must-show / must-hide / 3/2/1 mismatch를 체크한다.
3. 같은 장면이 과하게 3개로 과장되는지 본다.
4. WAIT 자리가 directional check처럼 보이지 않는지 본다.

### 완료 기준

- chart 기준으로 “이제 NAS는 내가 의도한 쪽으로 가고 있다”는 판단이 가능하다.

## 8. NAS4. Entry / Wait Tie-In

### 목표

chart 표기와 실제 entry/wait 체감이 서로 어긋나지 않게 만든다.

### 주 owner

- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)

### 핵심 원칙

- `3개 체크`는 `구조적으로 중요하다`는 뜻이지,
  자동으로 `READY`라는 뜻은 아니다.
- WAIT여야 하는 자리에서 2개/3개가 떠도
  실제 entry는 보수적으로 남아야 할 수 있다.

### 할 일

1. strong display but wait 사례를 casebook으로 본다.
2. late guard가 다시 chart 체감과 어긋나지 않는지 본다.
3. must-enter / must-block로 갈 장면을 좁혀서 본다.

### 완료 기준

- NAS에서 “차트는 좋은데 entry가 이상하다”는 mismatch가 줄어든다.

## 9. NAS5. Exit Sanity Review

### 목표

chart와 entry를 맞춘 뒤,
기다림/청산이 그 구조를 망치지 않는지 본다.

### 주 owner

- [wait_engine.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\wait_engine.py)
- [exit_profile_router.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_profile_router.py)
- [exit_manage_positions.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_manage_positions.py)

### 할 일

1. NAS good hold / bad hold 장면 분리
2. NAS good exit / premature exit 장면 분리
3. 3개 체크에서 바로 끊어버리는지, 반대로 너무 오래 버티는지 확인

### 완료 기준

- NAS가 chart/entry만 맞고 exit가 어색한 상태에서 벗어난다.

## 10. NAS6. Close-Out and Expansion Decision

### 목표

NAS에서 얻은 조정 방법을
다음 심볼에 확장할지, NAS만 더 반복할지 결정한다.

### 할 일

1. NAS acceptance close-out 메모 작성
2. 아래 중 하나 결정
- NAS second pass
- BTC first pass
- XAU first pass
- 다시 P7 overlay 검증 복귀

### 완료 기준

- NAS acceptance가 임시 수정이 아니라
  재사용 가능한 tuning pattern으로 정리된다.

## 11. 지금 당장 첫 액션

지금 가장 먼저 할 일은 아래다.

```text
NAS screenshot을 기준으로
3 / 2 / 1 / W / X casebook을 먼저 고정하고,
consumer_check_state + NAS symbol override를 우선 조정한다.
```

즉 첫 active step은 `NAS2`까지의 chart acceptance다.
entry/wait/exit는 NAS chart 표기가 어느 정도 맞은 뒤에 내려간다.

## 12. 한 줄 결론

이 NAS 로드맵의 핵심은 아래 한 줄이다.

```text
NAS는 painter부터 고치는 게 아니라,
사용자 screenshot을 정답 라벨로 삼고
consumer display importance와 NAS override를 먼저 다시 맞춘다.
```
