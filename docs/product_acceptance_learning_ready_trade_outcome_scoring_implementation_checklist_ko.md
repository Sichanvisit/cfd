# Product Acceptance Learning-Ready Trade Outcome Scoring Implementation Checklist

- [x] closed trade schema에 learning score surface 추가
- [x] normalizer가 새 컬럼을 유지하도록 반영
- [x] `add_signed_exit_score`에서 `entry / wait / exit / total` 계산
- [x] regression test 추가
- [x] runtime closed-history normalizer로 실제 값 확인

## done condition

- closed trade 한 줄만 보면 학습용 total reward를 바로 읽을 수 있음
