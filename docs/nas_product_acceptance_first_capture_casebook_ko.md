# NAS Product Acceptance First Capture Casebook

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 2026-03-30에 사용자가 제공한 첫 NAS screenshot을
실제 조정 가능한 `첫 casebook 샘플`로 고정하는 문서다.

이 문서는 아래 두 문서의 첫 실전 샘플 역할을 한다.

- [nas_product_acceptance_casebook_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\nas_product_acceptance_casebook_reference_ko.md)
- [nas_product_acceptance_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\nas_product_acceptance_execution_roadmap_ko.md)

## 2. 이번 screenshot에서 읽은 핵심 의도

사용자가 NAS 차트에 그린 흰색 동그라미는
`여기엔 의미 있는 체크 표기가 살아 있어야 한다`는 의도로 본다.

이번 screenshot은 크게 아래 3종 장면으로 읽는다.

### A. 박스 하단 반전/회복 시작

- 사용자가 가장 강하게 보고 싶은 장면
- lower box / lower recovery / reclaim start 계열
- 목표 표기: `3개 체크`

### B. 중간 눌림 후 재상승

- clean confirm 또는 stair-step 재가속 장면
- 상승 구조 안에서 다시 살아나는 눌림 자리
- 목표 표기: `2개 체크`

### C. 작은 continuation

- 추세가 이미 붙은 뒤의 작은 되돌림
- 흐름을 따라가는 약한 관찰 자리
- 목표 표기: `1개 체크`

## 3. 첫 screenshot의 장면군 분류

정확한 픽셀 좌표보다 `구조 장면군`으로 분류한다.

### 3-1. Zone L1: 좌하단 큰 박스 저점부

특징:

- 긴 하락/횡보 후 박스 하단에서 회복이 붙는 구간
- 이후 전체 상승 구조의 시작점처럼 보이는 자리

초기 라벨:

- `3`

의미:

- 이 구간은 NAS에서 가장 강하게 표시돼야 하는 시작점 후보다.
- 현재 시스템에서 단순 OBSERVE나 suppressed PROBE로 죽으면 부족한 것으로 본다.

### 3-2. Zone L2: 박스 상단 reclaim 직전과 직후

특징:

- 박스 내부에서 올라와 상단 reclaim을 시도하거나
  상단 reclaim 뒤 다시 흐름을 이어가는 구간

초기 라벨:

- reclaim 시작점은 `3`
- reclaim 뒤 첫 눌림은 `2`

의미:

- 구조 전환의 중심이므로
  continuation 수준보다 강하게 보여야 한다.

### 3-3. Zone M1: 중간 계단형 상승의 눌림-재상승

특징:

- red dashed guide / 짧은 눌림 뒤 다시 위로 붙는 구간
- clean confirm 성격이 반복되는 NAS 특유의 stair-step 장면

초기 라벨:

- `2`

의미:

- READY급은 아니어도
  1개 체크보다 더 분명한 관찰/프로브가 살아야 한다.

### 3-4. Zone M2: 중간 수평선 부근 돌파 후 재안착

특징:

- 흰 수평선 또는 중간 anchor 근처에서
  짧은 흔들림 뒤 다시 살아나는 구간

초기 라벨:

- `2`

의미:

- 단순 continuation보다 강하고,
  lower reversal만큼 무겁지는 않은 중간 강도의 NAS 장면이다.

### 3-5. Zone U1: 우상단 추세 continuation

특징:

- 이미 녹색 상승 구조가 살아난 뒤
  작은 눌림과 재가속이 이어지는 구간

초기 라벨:

- `1`

의미:

- 존재해야 하지만 과장되면 안 된다.
- 여기까지 2/3개가 과도하게 깔리면 chart가 시끄러워진다.

## 4. 아직 비어 있는 라벨

이번 첫 screenshot은 주로 `must-show` 중심이다.

아직 명확히 비어 있는 것은 아래다.

- `W` = WAIT여야 하는 자리
- `X` = 뜨면 안 되는 자리
- `R` = READY급이어야 하는 자리

즉 첫 pass는 `show strength`를 먼저 맞추고,
다음 screenshot부터 `WAIT/X/READY`를 보강하는 흐름이 맞다.

## 5. 현재 코드와 부딪히는 지점

현재 NAS는 이미 일부 규칙으로 눌려 있다.

### 5-1. NAS lower probe downgrade

현재 [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 에는
아래 성격의 규칙이 있다.

- `symbol = NAS100`
- `display_side = BUY`
- `observe_reason = lower_rebound_probe_observe`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = nas_clean_confirm_probe`

이면 `PROBE -> OBSERVE` 쪽으로 downgrade될 수 있다.

이 규칙은 Zone L1 / L2의 강도를 죽일 가능성이 있다.

### 5-2. NAS lower probe cadence suppression

같은 NAS lower rebound 장면에서
반복 signature가 비슷하면 `display_ready = False`로 내려버리는 suppression이 있다.

이 규칙은 사용자가 “여긴 여러 번 의미 있게 보여야 한다”고 보는 장면을
너무 쉽게 사라지게 만들 수 있다.

### 5-3. NAS structural cadence suppression

`outer_band_reversal_support_required_observe`
성격의 NAS 장면도 반복 시 suppression이 들어간다.

이 규칙은 Zone L1의 회복 시작 장면을
“조용히 지나가게” 만들 가능성이 있다.

## 6. 첫 adjustment 가설

이번 screenshot만 기준으로 한 첫 가설은 아래다.

### 가설 1

NAS lower recovery 시작점은
현재보다 `display_strength_level`이 한 단계 높아져야 한다.

### 가설 2

NAS clean confirm probe는
일괄 downgrade보다
`하단 반전 시작 / 중간 재상승 / continuation`을 나눠서 다뤄야 한다.

### 가설 3

현재 NAS cadence suppression은
“중복 노이즈 제거”에는 유효하지만,
사용자가 의미 있는 장면으로 보는 곳까지 숨기고 있을 수 있다.

## 7. 첫 조정 우선순위

이번 첫 capture 기준으로 조정 순서는 아래가 맞다.

1. `consumer_check_state.py`
- NAS lower rebound / clean confirm 관련
  `display_strength_level`, `display_score`, `display_repeat_count` 재조정

2. `consumer_check_state.py`
- `nas_lower_probe_downgrade`
- `nas_lower_probe_late_downgrade`
- `nas_lower_probe_cadence_suppressed`
- `nas_structural_cadence_suppressed`
  검토

3. `chart_symbol_override_policy.py`
- `nas_clean_confirm_probe` relief 범위 재점검

4. 그 다음에만 `chart_painter.py`
- translation noise가 있으면 마지막에 조정

## 8. 현재 결론

이번 첫 NAS screenshot은
`display ladder 전체를 갈아엎자`는 자료가 아니라,
`NAS lower recovery와 mid pullback을 현재보다 더 강하게 살려야 한다`는 자료로 본다.

즉 첫 착수의 방향은 아래 한 줄로 요약된다.

```text
NAS는 lower recovery와 중간 재상승을 더 강하게 살리고,
continuation은 약하게 남기며,
현재 clean_confirm_probe downgrade/suppression 규칙이 그 흐름을 과하게 누르는지 먼저 본다.
```
