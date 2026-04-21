# Teacher-Label State25 Labeler Memo

## 메모

이번 단계에서 중요한 건 `완벽한 자동 분류기`를 만드는 것이 아니라, 이미 고정된 state25 기준을 실제 compact row에 얹을 수 있는 첫 attach 레이어를 만드는 것이다.

## 이번 구현 판단

- schema는 이미 있으므로 이번엔 그릇이 아니라 실제 값 attach가 핵심이다.
- attach 시점은 open snapshot이 가장 자연스럽다.
- 이유:
  - 현재 시점 feature만 사용하기 쉽다.
  - open row에 한 번 붙이면 closed-history까지 carry된다.
  - look-ahead bias를 피하기 쉽다.

## 구현 원칙

- 명시 teacher 값이 있으면 라벨러는 덮어쓰지 않는다.
- explicit teacher 값이 비어 있을 때만 `rule_v2_draft`를 붙인다.
- primary minimum score 미만이면 unlabeled로 남긴다.
- secondary는 근접도 규칙을 통과할 때만 붙인다.

## 이번 초안의 의미

이 초안은 다음을 동시에 만족하는 중간층이다.

- 문서 기준과 맞닿아 있음
- compact dataset에 실제로 남음
- QA와 experiment가 바로 볼 수 있음
- execution 로직은 아직 건드리지 않음

즉 `state25를 말로만 정의해둔 상태`에서 `실제 row가 teacher-state를 갖는 상태`로 넘어가는 전환점이다.

## 다음 순서

1. QA gate
2. 1K / 10K 라벨링 분포 점검
3. confusion 상위 pair 보정
4. threshold / rare pattern / calibration 조정
