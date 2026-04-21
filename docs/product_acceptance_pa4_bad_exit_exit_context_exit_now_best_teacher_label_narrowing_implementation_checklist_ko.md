# Product Acceptance PA4 Bad Exit Exit Context Exit-Now-Best Narrowing Implementation Checklist

- [x] `bad_exit` 잔존 family closed-history ticket 재확인
- [x] `decision_reason / exit_wait_* / utility_*`가 freeze normalizer에 유지되는지 점검
- [x] `Exit Context + no_wait + exit_now_best + no post_exit_mfe`를 `bad_exit`에서 제외
- [x] 관련 regression test 추가
- [x] PA0 refreeze로 `bad_exit` 변화 확인

## done condition

- `bad_exit`에서 teacher-label 과대추정 family가 빠짐
- `must_release`는 별도 queue로 유지
