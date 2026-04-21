# Product Acceptance PA3 Teacher Label Wait Hold Acceptance Implementation Memo

## 상태

이 문서는 teacher-label 기준으로 PA3를 다시 보는 kickoff memo다.

현재 baseline 수치상 `must_hold = 0`이기 때문에
PA3는 이미 닫힌 것처럼 보인다.
하지만 스크린샷 기준으로는
`숫자상 잔여가 없더라도 hold correctness는 다시 볼 가치가 있다`
는 점을 확인했다.

즉 이번 PA3는 residue cleanup이 아니라
`hold가 맞았던 자리와 hold하면 안 되는 자리를 더 선명하게 가르는 작업`
이다.

## 연결 문서

- [product_acceptance_chart_capture_casebook_round1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_chart_capture_casebook_round1_ko.md)
- [product_acceptance_pa3_teacher_label_wait_hold_acceptance_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_teacher_label_wait_hold_acceptance_detailed_reference_ko.md)
- [product_acceptance_pa3_teacher_label_wait_hold_acceptance_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_teacher_label_wait_hold_acceptance_implementation_checklist_ko.md)

## 현재 판단

- NAS/XAU는 continuation hold와 release 시점을 같이 봐야 한다
- BTC는 hold correctness보다 bad hold 방지가 더 중요할 수 있다
- 따라서 PA3는 PA4와 인접하지만 별도로 분리해 기록하는 것이 맞다
