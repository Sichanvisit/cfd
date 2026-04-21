# Teacher-Label State25 Step 9-E4 Top Confusion Pair Tuning 메모

## 이번 단계에서 실제 본 것

- pilot baseline 기준 top group confusion은 `A -> D`
- top pattern confusion은 `1 -> 5`
- 기존 watchlist `12-23`, `5-10`, `2-16`은 current seed에서 거의 안 보임

즉 E4는 이론 watchlist보다
실제 현재 seed에서 먼저 보이는 pair를 좁게 다루는 게 맞았습니다.

## 구현 포인트

- confusion tuning report service 추가
- relabel provenance를 `rule_v2_tuned_relabel`로 분리
- labeler에서:
  - explicit range reversal setup이 있으면 1 fallback 축소
  - 5 proxy 강화
  - 13 fallback 축소
  - 14 session-only fallback 차단

## 현재 결과 해석

bounded relabel은 실제로 동작했고,
preview 상 recent `2K`에 대해 relabel된 row도 확인됐습니다.

다만 current seed 전체 pattern 분포와 pilot baseline confusion은
눈에 띄게 바뀌진 않았습니다.

이건 E4 실패라기보다:

- recent sparse row가 여전히 많고
- explicit micro detail이 없는 row는 fallback 구조가 강하고
- current labeled seed가 이미 `1 / 5 / 14 / 9` 위주로 굳어져 있기 때문

입니다.

즉 E4 첫 보정은 들어갔지만,
지금 단계에서 더 큰 변화는 `추가 labeled row 누적`이 같이 와야 보이게 됩니다.

## 운영 해석

현재 E4는:

- 구현 완료
- current confusion 우선순위 문서화 완료
- seed에 첫 bounded tuning 적용 완료

상태로 닫아도 됩니다.

다음은:

- labeled row 더 누적
- watchlist pair가 실제로 잡히는지 관측
- 그 뒤 E5 execution handoff 여부 판단

으로 가는 게 맞습니다.
