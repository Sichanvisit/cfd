# Check-First Display Gate Implementation Checklist

## Status

이 checklist는 더 이상 active checklist가 아니다.

이유:

- `display gate`를 painter 중심으로 구현하는 방향은 현재 owner 분리 원칙과 맞지 않는다
- 체크와 진입을 같은 Consumer chain으로 묶어야 한다

현재 active checklist:

- [consumer_coupled_check_entry_alignment_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_alignment_implementation_checklist_ko.md)

## Note

차트 가시성 follow-up 자체가 잘못된 것은 아니다.

다만 앞으로의 구현은:

- painter 독자 판단 강화

가 아니라

- Consumer canonical payload를 chart와 entry가 같이 소비

하는 방향으로 진행한다.
