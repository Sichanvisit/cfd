# Consumer-Coupled Check Visual Binding Follow-up

## 목적

`consumer_check_state_v1`가 live row에 내려와도,
chart가 그 `display_strength_level`을 색/두께에 직접 반영하지 않으면
체크 stage 차이가 화면에서 잘 안 보인다.

이번 follow-up의 목적은:

- `PROBE / READY / WAIT` 스타일을 strength 기준으로 통일하고
- 특히 probe도 wait/ready처럼 색 차이가 나게 만드는 것이다.

## 반영 내용

수정 파일:

- [chart_flow_policy.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [chart_painter.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- [test_chart_painter.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)

핵심 변경:

1. `BUY_PROBE`, `SELL_PROBE`를 strength color binding 대상에 포함
2. `consumer_check_state_v1.display_strength_level`이 있으면
   painter가 그 level을 우선 사용
3. level이 있으면 score도 최소 수준으로 맞춰서
   color/width 계산이 stage-strength와 어긋나지 않게 함
4. marker 기본 크기를 policy로 분리
   - `marker_time_scale = 0.50`
   - `marker_price_scale = 0.50`
   - `probe_marker_time_scale = 0.50`
   - `probe_marker_price_scale = 0.50`
   - `neutral_marker_time_scale = 0.50`
   - `neutral_marker_price_scale = 0.50`

## 기대 효과

- 약한 probe는 더 얇고 덜 밝게
- 강한 probe는 더 굵고 더 밝게
- ready는 probe보다 강하게 보이고
- blocked/weak wait는 상대적으로 덜 튀게 보임
- 전반적인 체크 도형 길이와 높이가 이전 대비 약 50% 수준으로 줄어듦

즉 같은 consumer chain이라도 화면에서 단계 차이가 더 잘 보이게 된다.

## 테스트

- `pytest tests/unit/test_chart_painter.py -q` -> `55 passed`
- `pytest tests/unit/test_entry_service_guards.py tests/unit/test_chart_painter.py -q` -> `115 passed`

## 현재 해석

이제 chart style 쪽의 남은 문제는
`stage/strength가 반영되느냐`가 아니라
`어떤 stage를 실제로 surface할 것이냐`의 정책 문제다.

즉 다음 조정은:

- `PROBE`를 얼마나 자주 보여줄지
- `BLOCKED`를 directional wait로 남길지 더 눌러줄지
- symbol/scene별 density tuning
