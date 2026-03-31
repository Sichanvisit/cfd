# NAS Product Acceptance Casebook Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `제품 acceptance 재정렬` 트랙 중에서도
`NAS100`을 첫 심볼로 고정해서,

- 사용자가 차트에서 보고 싶은 체크 표기
- 그 표기와 실제 실행 준비도의 관계
- 어떤 owner와 어떤 파라미터를 먼저 조정해야 하는지

를 NAS 기준으로 구체화한 casebook reference다.

상위 기준 문서는 아래 두 문서다.

- [product_acceptance_reorientation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_detailed_reference_ko.md)
- [product_acceptance_reorientation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_execution_roadmap_ko.md)

현재 첫 실전 샘플은 아래 문서를 같이 본다.

- [nas_product_acceptance_first_capture_casebook_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\nas_product_acceptance_first_capture_casebook_ko.md)
- [nas_product_acceptance_initial_adjustment_targets_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\nas_product_acceptance_initial_adjustment_targets_ko.md)

이 문서는 `NAS만 먼저 제대로 맞춘다`는 전제로 쓴다.

## 2. 시작점: 사용자가 NAS 스크린샷에서 보여준 의도

2026-03-30 KST 기준 사용자가 제공한 NAS 차트 스크린샷에는
흰색 동그라미가 다수 표시돼 있고,
그 동그라미는 대체로 아래 의도를 가진 것으로 해석한다.

### 2-1. 3개 체크가 필요한 자리

- 박스 하단 반전/회복 시작점
- 큰 구조 전환이 처음 살아나는 자리
- “여기는 NAS에서 강하게 보여야 한다”는 자리

### 2-2. 2개 체크가 필요한 자리

- 중간 눌림 후 재상승 자리
- clean confirm 성격의 재가속 후보
- 강하지만 최강은 아닌 구조 자리

### 2-3. 1개 체크가 필요한 자리

- 추세가 붙은 뒤 작은 되돌림 continuation 자리
- 흐름을 따라가는 약한 관찰 자리
- 체크는 있어야 하지만 과장되면 안 되는 자리

### 2-4. 함께 분리해야 하는 것

위 `3/2/1 체크`는 `구조 중요도` 기준이다.

이건 아래와 분리해서 다뤄야 한다.

- `WAIT`
- `PROBE`
- `READY`
- `BLOCKED`

즉 NAS에서 우리가 원하는 건
`체크 개수 = 구조 중요도`
`실행 준비도 = WAIT/PROBE/READY/BLOCKED`
로 분리된 시스템이다.

## 3. 현재 NAS가 실제로 쓰고 있는 체계

현재 NAS는 새 시스템이 아니라
이미 구축된 display ladder와 consumer chain 위에서 움직이고 있다.

### 3-1. 현재 display ladder

현행 repeat threshold는 아래와 같다.

- `0.70 ~ 0.79` -> `1개 체크`
- `0.80 ~ 0.89` -> `2개 체크`
- `>= 0.90` -> `3개 체크`

기준 owner:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)

### 3-2. 현재 stage와 display의 결합

현재는 대체로 아래처럼 묶여 있다.

- `OBSERVE` -> `1개 체크`
- `PROBE` -> `2개 체크`
- `READY` -> `3개 체크`

즉 현재 시스템은
`체크 개수 = 실행 단계`
에 더 가깝고,
사용자가 원하는
`체크 개수 = 구조 중요도`
와는 완전히 같지 않다.

### 3-3. 현재 NAS 전용 override

NAS는 이미 일부 전용 override가 있다.

- router probe clean confirm
- clean confirm middle anchor relief
- painter scene allow `nas_clean_confirm_probe`

기준 owner:

- [chart_symbol_override_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_symbol_override_policy.py)

즉 NAS는 지금도 generic symbol이 아니라,
이미 별도 조정 레일 위에 올라가 있다.

## 4. NAS acceptance에서 먼저 맞춰야 하는 해석

### 4-1. 우리가 유지할 것

- 기존 consumer chain 자체
- `consumer_check_state_v1` 계약
- `0.70 / 0.80 / 0.90` ladder 자체
- late guard와 runtime reconciliation 구조

### 4-2. 우리가 다시 맞출 것

- NAS에서 어떤 장면이 `3개/2개/1개`로 보여야 하는지
- 같은 `PROBE`라도 어떤 건 `3개`, 어떤 건 `2개`로 보여야 하는지
- `WAIT`가 약한 BUY 체크처럼 보이지 않게 하는 것
- 차트의 강한 표기가 바로 live open 의미가 되지 않게 하는 것

즉 NAS acceptance의 첫 목표는
`stage 중심 ladder`를 없애는 게 아니라,
`구조 중요도 uplift/downgrade`를 NAS에 먼저 연결하는 것이다.

## 5. NAS screenshot을 코드에 연결할 때의 기준

### 5-1. 입력 casebook 라벨

앞으로 NAS 스크린샷에는 최소한 아래 라벨만 있으면 된다.

- `3` = 3개 체크
- `2` = 2개 체크
- `1` = 1개 체크
- `W` = WAIT여야 함
- `X` = 뜨면 안 됨

가능하면 아래 보조 라벨을 같이 붙인다.

- `R` = READY급이어야 함
- `P` = PROBE급이어야 함
- `W2` = WAIT이지만 방향 bias는 느껴져야 함

예:

- `3-P`
- `2-W`
- `1-P`
- `X`

하지만 첫 NAS pass는 숫자만으로도 시작 가능하다.

### 5-2. chart 표기와 실행 준비도를 분리해서 읽는 규칙

- `3`이라고 해서 곧바로 `READY`를 뜻하지 않는다.
- `2`라고 해서 entry를 열어야 한다는 뜻은 아니다.
- `1`은 continuation 관찰용일 수 있다.
- `W`는 방향 bias가 있더라도 open-ready가 아니어야 한다.

즉 숫자는 `표기 강도`, stage는 `실행 준비도`다.

## 6. NAS에서 실제로 먼저 건드릴 owner

### 6-1. 1순위: display importance 계산

첫 owner:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)

먼저 건드릴 포인트:

- `display_strength_level`
- `display_score`
- `display_repeat_count`
- NAS-specific uplift/downgrade rule

여기서 해야 하는 일:

- NAS lower recovery 시작점을 `3개 체크` 쪽으로 올릴 규칙
- NAS clean confirm 재상승을 `2개 체크`로 안정화할 규칙
- NAS continuation은 `1개 체크`로 남길 규칙
- `WAIT`가 억지로 1개/2개 BUY처럼 보이지 않게 할 규칙

### 6-2. 2순위: NAS scene allow / relief

두 번째 owner:

- [chart_symbol_override_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_symbol_override_policy.py)

여기서 해야 하는 일:

- `nas_clean_confirm_probe`만으로 부족한지 확인
- NAS lower recovery / box rebound / continuation 성격을
  별도 scene allow 또는 relief knob로 분리할지 검토

### 6-3. 3순위: painter는 translation만 조정

세 번째 owner:

- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)

여기서 할 일은 제한적이다.

- upstream에서 repeat_count가 맞게 오면 painter는 translation만 한다.
- painter는 마지막 수단으로만 건드린다.
- 먼저 `consumer_check_state`와 `symbol override`를 맞춘다.

### 6-4. 4순위: entry/wait 연결

chart가 어느 정도 맞은 다음에야 아래 owner를 본다.

- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)

여기서 확인할 일:

- 강한 체크인데 아직 WAIT여야 하는 장면이 잘 유지되는지
- 차트에 3개가 떴다고 바로 열리지 않는지
- late guard가 chart 체감과 다시 어긋나지 않는지

## 7. NAS 첫 acceptance에서 기대하는 변화

NAS 첫 pass가 잘 되면 차트 체감은 아래처럼 바뀌어야 한다.

- 박스 하단 반전/회복 시작은 `3개 체크`로 강하게 보인다.
- 중간 눌림 후 재상승은 `2개 체크`로 살아난다.
- 추세 continuation은 `1개 체크`로 가볍게 따라간다.
- WAIT 구간은 방향성 체크와 헷갈리지 않는다.
- chart가 “강하게 보이는 것”과 live entry가 “실제로 열리는 것”이 분리된다.

## 8. 완료 기준

이 문서 기준 NAS acceptance가 1차로 닫혔다고 말하려면 아래가 필요하다.

- 사용자가 표시한 NAS screenshot casebook을
  `3 / 2 / 1 / W / X`로 재표현할 수 있다.
- 현재 chart output이 그 casebook에 가까워진다.
- `3개 체크`와 `READY`가 자동으로 같은 의미가 아니게 된다.
- NAS에서 “이 자리는 세게 보이고, 이 자리는 약하게 보이며,
  이 자리는 WAIT다”라는 체감이 사용자의 의도와 가까워진다.

## 9. 한 줄 결론

NAS first acceptance의 핵심은 아래 한 줄이다.

```text
기존 ladder를 버리는 게 아니라,
NAS에서만 먼저 "체크 개수 = 구조 중요도"가 되도록
consumer state와 symbol override를 다시 연결한다.
```
