# XAU Product Acceptance Casebook Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `XAUUSD` 차트를 기준으로,

- 사용자가 차트에서 보고 싶어 하는 체크 표기
- 그 표기와 실제 실행 준비도의 관계
- 어떤 owner와 어떤 파라미터를 먼저 조정해야 하는지

를 XAU 관점으로 고정하기 위한 casebook reference다.

상위 기준 문서는 아래 두 문서다.

- [product_acceptance_reorientation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_detailed_reference_ko.md)
- [product_acceptance_reorientation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_execution_roadmap_ko.md)

이번 XAU 첫 샘플과 첫 조정 메모는 아래 문서를 같이 본다.

- [xau_product_acceptance_first_capture_casebook_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\xau_product_acceptance_first_capture_casebook_ko.md)
- [xau_product_acceptance_initial_adjustment_targets_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\xau_product_acceptance_initial_adjustment_targets_ko.md)
- [xau_product_acceptance_first_adjustment_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\xau_product_acceptance_first_adjustment_implementation_memo_ko.md)

## 2. XAU에서 원하는 표기 원칙

### 2-1. `3개 체크`

아래 성격의 장면은 XAU에서 강하게 보여야 한다.

- 박스 하단 반전/회복 시작
- 깊은 눌림 뒤 강한 회복 시작
- 상단 핵심 reject/upper break fail 핵심 자리

### 2-2. `2개 체크`

아래 성격의 장면은 의미 있는 구조지만 최강은 아니다.

- 두 번째 지지(second support) 반등
- middle reclaim 이후 다시 붙는 반등
- upper reject 전개 중 아직 완전 핵심 confirm 전 단계

### 2-3. `1개 체크`

아래 성격의 장면은 흐름 추적 수준으로만 보여야 한다.

- 이미 성숙한 continuation
- 의미는 있지만 과장되면 안 되는 작은 되돌림

### 2-4. 분리 원칙

XAU도 NAS와 동일하게 아래를 분리한다.

- `3/2/1 체크` = 구조 중요도
- `WAIT / PROBE / READY / BLOCKED` = 실행 준비도

즉 `3개 체크`라고 해서 반드시 `READY`는 아니다.

## 3. 현재 XAU owner 구조

핵심 owner는 아래다.

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_symbol_override_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_symbol_override_policy.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)

이번 첫 패스의 실질 owner는 `consumer_check_state`다.

## 4. XAU에서 이미 강하게 들어가 있는 억제 규칙

XAU는 기존부터 상단 reject 쪽 과표시를 막기 위한 억제 규칙이 있었다.

- `xau_upper_reject_confirm_hidden`
- `xau_upper_reject_guard_wait_hidden`
- `xau_upper_sell_repeat_suppressed`
- `xau_upper_reject_cadence_suppressed`
- `xau_middle_anchor_cadence_suppressed`

첫 패스에서는 이 규칙들을 해제하지 않는다.

이유:

- XAU는 NAS보다 상하 혼합 신호가 많다
- 상단 reject를 한 번에 다 열면 차트 해석성이 다시 무너질 수 있다
- 이번 패스의 목적은 `좋은 자리 살리기`이지 `기존 보호장치 해제`가 아니다

## 5. 첫 패스에서 살리려는 XAU 장면

### 5-1. 하단 회복 시작

- `lower_rebound_confirm`
- `lower_rebound_probe_observe`
- lower context (`box_state=BELOW`, `bb_state=LOWER_EDGE/BREAKDOWN`)

의도:

- `3개 체크`
- stage는 owner에 따라 `PROBE` 또는 `OBSERVE`일 수 있음

### 5-2. second support / middle reclaim 반등

- `outer_band_reversal_support_required_observe`
- `middle_sr_anchor_required_observe`
- `probe_scene_id = xau_second_support_buy_probe`

의도:

- `2개 체크`
- 아직 기다림/관찰 단계여도 구조 중요도는 medium으로 보이게

### 5-3. 상단 핵심 reject / break fail

- `upper_reject_probe_observe`
- `upper_reject_confirm`
- `upper_reject_mixed_confirm`
- `upper_break_fail_confirm`
- `probe_scene_id = xau_upper_sell_probe`

의도:

- 핵심 upper reject confirm / break fail은 `3개 체크`
- 그 외 upper reject 전개는 `2개 체크` 우선
- 단, guard wait 상황에서는 여전히 숨김 유지

## 6. 아직 이번 패스에서 안 건드린 것

- `WAIT / X`의 정밀 라벨링
- XAU entry/wait/exit acceptance 본격 조정
- 상단 mature continuation의 세밀한 soft cap
- live execution gate 수정

즉 첫 패스는 chart importance 조정까지만 다룬다.

## 7. 다음 확인 포인트

다음 XAU 스크린샷에서는 아래를 본다.

- 하단 회복 시작이 실제로 3개로 살아났는지
- second support 반등이 2개로 보이는지
- 상단 reject 핵심만 살아나고, 상단 전 구간이 confetti처럼 되지 않는지
- forecast/barrier wait에서 숨겨야 할 upper reject는 여전히 안 보이는지
