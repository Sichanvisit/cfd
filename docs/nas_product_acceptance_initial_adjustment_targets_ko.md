# NAS Product Acceptance Initial Adjustment Targets

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 첫 NAS screenshot casebook을 기준으로
`어떤 파일의 어떤 규칙부터 조정 후보로 볼지`
를 짧고 실전적으로 정리한 메모다.

기준 문서는 아래를 본다.

- [nas_product_acceptance_first_capture_casebook_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\nas_product_acceptance_first_capture_casebook_ko.md)
- [nas_product_acceptance_casebook_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\nas_product_acceptance_casebook_reference_ko.md)

## 2. 조정 목표 한 줄

```text
NAS에서는 "박스 하단 반전/회복 시작 = 3개",
"중간 눌림 재상승 = 2개",
"작은 continuation = 1개"가 chart 체감에 먼저 반영돼야 한다.
```

## 3. 1순위 조정 owner

### [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)

가장 먼저 볼 항목:

- `display_strength_level`
- `display_score`
- `display_repeat_count`

첫 조정 방향:

- NAS lower recovery 시작점 uplift
- NAS mid pullback re-up 2-check 고정
- continuation 과표시 방지

## 4. 2순위 조정 후보 규칙

### NAS lower probe downgrade 계열

먼저 의심할 규칙:

- `nas_lower_probe_downgrade`
- `nas_lower_probe_late_downgrade`

이유:

- 사용자가 3개/2개로 보고 싶은 lower recovery / reclaim 시작이
  일괄 downgrade로 약화될 수 있다.

### NAS cadence suppression 계열

먼저 의심할 규칙:

- `nas_lower_probe_cadence_suppressed`
- `nas_structural_cadence_suppressed`

이유:

- NAS에서는 비슷한 구조가 stair-step으로 반복되는데,
  이걸 noise 중복으로만 읽으면
  사용자가 원하는 반복 체크가 사라질 수 있다.

## 5. 3순위 조정 owner

### [chart_symbol_override_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_symbol_override_policy.py)

현재 NAS 관련 knob:

- `router.probe.clean_confirm`
- `router.relief.clean_confirm_middle_anchor`
- `painter.scene_allow.nas_clean_confirm_probe`

조정 질문:

- 현재 clean confirm probe relief가 lower recovery를 충분히 살리고 있는가
- 중간 눌림 재상승 장면을 2-check로 보일 만큼 열어주고 있는가

## 6. 아직 나중에 볼 것

### [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)

지금은 후순위다.

이유:

- painter는 repeat_count와 display_score를 번역하는 층이다.
- upstream이 맞지 않으면 painter 조정은 임시봉합이 된다.

### [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
### [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)

chart 첫 pass가 끝난 뒤 본다.

이유:

- 지금 screenshot은 `must-show` 위주이고
  아직 `must-enter / must-block / W / X` 라벨이 부족하다.

## 7. 바로 다음 액션

지금 당장 코딩에 들어가기 전,
다음 한 가지를 먼저 고정하는 게 좋다.

```text
현재 NAS screenshot의 동그라미들을
Zone L1/L2/M1/M2/U1 기준으로 한 번 더 정리하고,
각 zone을 3/2/1 중 어디로 볼지 최종 고정한다.
```

이게 고정되면 그 다음엔
`consumer_check_state.py` 조정으로 바로 들어갈 수 있다.

## 8. 한 줄 결론

첫 NAS 조정은 painter가 아니라
`consumer_check_state + NAS-specific downgrade/suppression 규칙`
부터 보는 게 맞다.
