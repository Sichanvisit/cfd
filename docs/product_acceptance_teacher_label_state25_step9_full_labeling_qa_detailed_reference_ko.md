# Teacher-Label State25 Step E2 Full Labeling QA 상세 기준서

## 목적

Step E2의 목적은 `10K full labeling QA`를 돌릴 수 있는 리포트 체계를 먼저 만드는 것이다.

이 단계는 아직 execution으로 가는 단계가 아니다.

- 현재 labeled seed가 어떤 패턴에 치우쳐 있는지
- 25개 패턴이 얼마나 실제로 덮였는지
- primary/secondary pair가 어디에 몰리는지
- symbol별 분포가 얼마나 왜곡됐는지

를 `실험 가능한 숫자`로 고정하는 단계다.

## 왜 필요한가

현재 Step 8 QA gate는

- 라벨이 붙었는지
- provenance가 정상인지
- rare/low-confidence 경고가 있는지

까지는 잘 잡아준다.

하지만 Step 9 본론에서 필요한 건 그보다 더 구체적이다.

- `10K` 목표 대비 현재 shortfall
- 25개 패턴 coverage
- missing pattern
- symbol별 group skew
- primary-secondary pair concentration
- confusion proxy pair

즉 Step E2는 `품질 gate`가 아니라 `분포/쏠림/혼동 준비도 리포트`다.

## 필수 출력

### 1. full QA readiness

- `min_labeled_rows`
- `full_qa_ready`
- `shortfall_rows`

### 2. pattern coverage

- 25개 primary pattern 전체 분포
- secondary pattern 전체 분포
- covered primary count
- missing primary ids
- rare primary ids

### 3. group / symbol 분포

- overall group distribution
- symbol별 row 수
- symbol별 top primary pattern
- symbol별 covered primary count
- symbol별 missing primary ids
- symbol별 top group / top group ratio

### 4. confusion proxy

ground-truth confusion matrix는 아직 없다.
대신 현재 단계에서는 `primary-secondary pair`를 confusion proxy로 본다.

- 전체 primary-secondary pair 분포
- watchlist pair (`12-23`, `5-10`, `2-16`)
- 과집중 pair 경고

### 5. bias / confidence / provenance bridge

Step E1 seed report가 이미 갖고 있는 아래 정보는 그대로 bridge한다.

- source distribution
- review status distribution
- bias distribution
- confidence summary
- rare pattern warnings
- low confidence review target

## 구현 owner

- [teacher_pattern_full_labeling_qa.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_full_labeling_qa.py)
- [teacher_pattern_full_labeling_qa_report.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/teacher_pattern_full_labeling_qa_report.py)
- [test_teacher_pattern_full_labeling_qa.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_teacher_pattern_full_labeling_qa.py)

## 완료 기준

- Step E2 report builder 추가
- CLI report 추가
- Step E1 seed report bridge 연결
- missing/rare/group_skew/pair_concentration 경고 추가
- 실제 현재 compact dataset에 한 번 실행해서 결과 확인

## 다음 단계 연결

이 단계가 닫히면 다음은 아래 순서다.

1. 현재 seed(`2K+`)에 Step E2 report 적용
2. skew와 missing pattern 확인
3. Step E3 baseline model 준비
4. Step E4 top confusion pair tuning

## 운영 해석 원칙

Step E2에서 `group skew`나 `missing primary ids`가 나온다고 해서,
그 자체를 곧바로 라벨러 실패로 해석하면 안 된다.

이 프로젝트의 전제는 다음과 같다.

- 시장은 원래 균등하지 않다.
- 조용한 장과 압축장이 대부분이고, 발작장/원웨이장/희귀 반전장은 드물다.
- 따라서 `25개 패턴을 균등 빈도`로 맞추는 것이 목표가 아니다.

즉 Step E2의 역할은 `균형 여부를 평가해 합격/불합격을 내리는 것`이 아니라,
현재 seed가 어느 패턴에 치우쳐 있는지와 어떤 패턴이 아직 덜 쌓였는지를
실험 단계에서 해석할 수 있게 만드는 것이다.

## skew를 어떻게 해석할 것인가

현재와 같이 `A 그룹` 비율이 높게 나오는 것은
시장 현실상 자연스러운 결과일 수 있다.

따라서 아래처럼 해석한다.

- `overall_group_skew`:
  시장 구조상 다수 장세가 우세하다는 의미일 수 있다.
- `missing_primary_patterns_present`:
  라벨러 실패라기보다 아직 해당 장세가 충분히 관찰되지 않았을 가능성이 크다.
- `rare_primary_patterns_present`:
  희귀 패턴이므로 장기 누적과 별도 버퍼 관리 대상으로 본다.

즉 Step E2 경고는 `즉시 수정해야 하는 오류`보다
`이후 실험에서 보정해야 하는 불균형 정보`로 읽는 게 맞다.

## Step E2 이후 운영 판단

현재 seed가 `25개 전체 대표성`은 아직 부족해도,
아래 목적에는 충분히 사용할 수 있다.

- pipeline sanity check
- 라벨러 초기 품질 점검
- 작은 pilot baseline
- bias/confidence/provenance 점검

반대로 아래 목적에는 더 많은 누적이 필요하다.

- 25개 전체 baseline
- top confusion pair 본격 튜닝
- execution handoff 판단

## 실험 단계에서의 보정 원칙

Step E2 결과가 skew되어 있어도,
다음 단계에서는 이를 아래 방식으로 보정한다.

- class weight 사용
- stratified sampling 사용
- rolling window 유지
- rare pattern buffer는 더 오래 보관
- raw는 purge하더라도 compact labeled row는 유지

즉 해결 방향은 `지금 skew를 없애는 것`이 아니라,
`계속 누적하면서 학습 단계에서 불균형을 다루는 것`이다.
