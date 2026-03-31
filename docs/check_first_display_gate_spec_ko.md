# Check-First Display Gate Spec

## Status

이 문서는 `painter/display gate` 중심으로 생각하던 초기 초안이며, 현재 구현 기준 문서가 아니다.

이 초안은 아래 이유로 더 이상 기준으로 쓰지 않는다.

- chart 표기 owner가 과하게 커질 수 있다
- `Consumer`와 chart가 서로 다른 판단 체계를 가질 위험이 있다
- 체크와 실제 진입이 같은 semantic/consumer chain에서 설명되지 않을 수 있다

현재 유효한 기준 문서는 아래 두 개다.

- [consumer_coupled_check_entry_alignment_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_alignment_spec_ko.md)
- [consumer_coupled_check_entry_alignment_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_alignment_implementation_checklist_ko.md)

## Why Deprecated

현재 chart_flow 안정화의 핵심 원칙은 그대로 유지된다.

- 의미 owner는 router
- 실행 승격 owner는 consumer/entry
- painter는 번역 owner
- ML은 의미 owner가 아니라 같은 chain의 threshold/score 보조

따라서 체크 표기를 더 좋게 만들더라도, 별도 painter gate를 독립 owner처럼 두는 방식은 쓰지 않는다.
