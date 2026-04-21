# Teacher-Label State25 Labeling QA 메모

## 메모

- 외부 조언 중 `look-ahead bias`, `검수 프로세스`, `confusion pair`, `희소 패턴 감시`는 학습이 알아서 해결해주지 않는 항목이다.
- 따라서 이 네 축은 실험으로 미루지 않고 지금 운영 규칙으로 고정하는 것이 맞다.

## 이번 단계 결정

- 라벨링 QA를 별도 단계로 둔다.
- `라벨 품질 관리`와 `모델 실험 조정`을 분리한다.
- QA 단계는 사람이 읽는 문서와 체크리스트로 먼저 닫는다.

## 지금 고정한 것

- look-ahead bias 금지
- 2단계 검수 프로세스
- confusion pair watchlist
- 희소 패턴 경고
- post-label QA checklist

## 의도적으로 고정하지 않은 것

- 자산별 ATR 실제 분포 수치
- train/val/test split 비율
- baseline 모델 목표치
- execution 반영 기준

## 후속 단계

- 다음은 `teacher_pattern_* compact dataset 스키마`를 만들고,
- 그 다음 `Step 9 experiment tuning roadmap`에 따라 1K/10K 단위로 실험 조정을 하면 된다.
