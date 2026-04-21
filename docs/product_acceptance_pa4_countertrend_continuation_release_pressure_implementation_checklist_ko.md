# Product Acceptance PA4 Countertrend Continuation Release Pressure Implementation Checklist

- [x] `must_release 8` family 대표 closed-trade row 확인
- [x] `countertrend_with_entry / topdown_state_label / giveback / peak_profit`로 표현 가능한지 owner 점검
- [x] continuation release pressure runtime bias 추가
- [x] regression test 추가
- [x] runtime 재기동

## done condition

- 반대 continuation + 의미 있는 giveback family에서 `exit_now` bias가 더 강해짐
- next fresh close부터 새 pressure가 반영될 준비가 됨
