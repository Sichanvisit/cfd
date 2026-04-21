# BC9 State25 Threshold Bounded Live 실행 로드맵

## 단계

1. threshold active state contract 정리
- bounded live delta / direction / reason keys

2. threshold apply handler 추가
- `STATE25_THRESHOLD_PATCH_REVIEW`
- `log_only` / `bounded_live` 둘 다 처리

3. entry consumption 연결
- `resolve_state25_candidate_live_threshold_adjustment_v1`
- `entry_try_open_entry.py`에서 실제 `dynamic_threshold` 반영

4. runtime trace 확인
- before / after / delta / direction

5. 테스트
- active candidate runtime helper
- threshold apply handler
- threshold review builder

## 완료 기준

- threshold bounded live patch를 승인하면 active candidate state가 `bounded_live`로 저장된다.
- entry runtime에서 threshold before/after가 실제로 바뀐다.
- log-only threshold와 bounded live threshold가 contract 수준에서 분리된다.
