# BTC Product Acceptance Casebook Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `BTCUSD` 차트를 기준으로,

- 사용자가 보고 싶어 하는 체크 강도
- 그 체크와 실제 실행 준비도의 관계
- 어떤 owner와 어떤 파라미터를 먼저 조정해야 하는지

를 BTC 관점으로 고정하기 위한 casebook reference다.

상위 기준 문서는 아래다.

- [product_acceptance_reorientation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_detailed_reference_ko.md)
- [product_acceptance_reorientation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_execution_roadmap_ko.md)

이번 BTC 첫 샘플과 첫 조정 메모는 아래 문서를 같이 본다.

- [btc_product_acceptance_first_capture_casebook_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\btc_product_acceptance_first_capture_casebook_ko.md)
- [btc_product_acceptance_initial_adjustment_targets_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\btc_product_acceptance_initial_adjustment_targets_ko.md)
- [btc_product_acceptance_first_adjustment_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\btc_product_acceptance_first_adjustment_implementation_memo_ko.md)

## 2. BTC에서 원하는 표기 원칙

### 2-1. `3개 체크`

아래 성격의 장면은 BTC에서 강하게 보여야 한다.

- 깊은 하단 반전/회복 시작
- lower breakdown 이후 강한 reclaim 시작

### 2-2. `2개 체크`

아래 성격의 장면은 의미 있는 구조지만 최강은 아니다.

- middle reclaim 이후 다시 붙는 반등
- lower structural rebound
- 보수적 lower probe의 핵심 continuation

### 2-3. `1개 체크`

아래 성격의 장면은 흐름 추적 수준으로만 보여야 한다.

- 이미 충분히 진행된 상단 continuation
- 의미는 있지만 과장되면 안 되는 작은 되돌림

### 2-4. 분리 원칙

BTC도 NAS/XAU와 동일하게 아래를 분리한다.

- `3/2/1 체크` = 구조 중요도
- `WAIT / PROBE / READY / BLOCKED` = 실행 준비도

즉 `3개 체크`라도 반드시 `READY`는 아니다.

## 3. 현재 BTC owner 구조

핵심 owner는 아래다.

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_symbol_override_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_symbol_override_policy.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)

이번 첫 패스의 실질 owner는 `consumer_check_state`다.

## 4. BTC에서 이미 들어가 있는 보호장치

BTC는 lower probe가 너무 많이 반복되는 걸 막기 위한 기존 규칙이 있다.

- `btc_lower_probe_downgrade`
- `btc_lower_probe_late_downgrade`
- `btc_lower_structural_cadence_suppressed`
- `btc_lower_probe_cadence_suppressed`

첫 패스에서는 이 규칙들을 풀지 않는다.

이유:

- BTC는 lower buy 쪽을 살리되 남발이 생기면 차트 해석성이 빠르게 무너진다
- 첫 패스의 목적은 `좋은 자리 uplift`이지 `기존 cadence 보호장치 해제`가 아니다

## 5. 첫 패스에서 살리려는 BTC 장면

### 5-1. 하단 회복 시작

- `lower_rebound_confirm`
- `lower_rebound_probe_observe`
- `probe_scene_id = btc_lower_buy_conservative_probe`

문맥:

- lower context (`box_state=BELOW`, `bb_state=LOWER_EDGE/BREAKDOWN`)

의도:

- `3개 체크`

### 5-2. middle reclaim / structural rebound

- `outer_band_reversal_support_required_observe`
- `middle_sr_anchor_required_observe`
- `probe_scene_id = btc_lower_buy_conservative_probe`

문맥:

- lower / middle reclaim

의도:

- `2개 체크`

### 5-3. 상단 성숙 continuation

BTC upper continuation은 첫 패스에서 적극 uplift하지 않는다.

의도:

- 기본 `1개 체크`
- 과표시 금지

## 6. 아직 이번 패스에서 안 건드린 것

- `WAIT / X`의 정밀 라벨링
- BTC entry/wait/exit acceptance 본격 조정
- BTC upper continuation의 세밀한 별도 soft cap
- live execution gate 수정

즉 첫 패스는 chart importance 조정까지만 다룬다.

## 7. 다음 확인 포인트

다음 BTC 스크린샷에서는 아래를 본다.

- lower recovery가 실제로 3개로 살아났는지
- middle reclaim이 2개 수준으로 읽히는지
- upper continuation이 confetti처럼 늘어나지 않는지
- 기존 lower cadence suppression은 여전히 잘 작동하는지
