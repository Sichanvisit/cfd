# Teacher-Label Micro-Structure Top10 Step 8 메모

## 메모

- Step 8은 라벨 생성 단계가 아니라 라벨 점검 단계다.
- 이번 단계에서 중요한 것은 pattern score를 다시 만지는 것이 아니라
  `붙은 teacher-pattern row를 운영 기준으로 통과/경고/실패로 나누는 것`이다.
- watchlist pair, rare pattern, low-confidence review는 Step 9 실험 조정에서 바로 재사용된다.

## 이번 단계에서 본 주요 위험

- compact schema는 있어도 provenance가 비면 나중에 어떤 버전 기준으로 붙은 라벨인지 추적이 어렵다.
- primary/secondary pair를 ordered로 세면 confusion pair 해석이 흔들린다.
- rare pattern은 실제로 적게 나오는 것이 정상일 수 있지만, 존재 여부 자체를 안 보면 데이터셋 편향을 놓치기 쉽다.

## 구현 결과

- QA report builder를 추가해 compact dataset 한 덩어리를 받아:
  - labeled / unlabeled 분포
  - primary pattern 분포
  - watchlist pair 집계
  - rare watch pattern 경고
  - entry / wait / exit bias 분포
  - lowest-confidence 5% review target
  를 한 번에 뽑을 수 있게 했다.

## 다음 단계 연결

- Step 8이 닫히면 다음은 Step 9 experiment tuning이다.
- Step 9에서는 이 QA report를 바탕으로
  - 자산별 ATR 보정
  - confusion 상위쌍 조정
  - baseline split / metric
  을 다루면 된다.
