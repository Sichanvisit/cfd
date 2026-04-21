# Teacher-Label State25 Threshold Calibration 체크리스트

## 목표

`teacher-state 25`의 수치 기준을 v1 고정 절대치 중심에서 `v2 hybrid threshold` 기준으로 정리한다.

## Step 1. 문서 기준 확정

- [ ] `고정 절대치 유지` 패턴과 `ATR 정규화 전환` 패턴을 분리한다.
- [ ] `도지`, `거래량 burst`, `압축`, `재시험` 전역 보정 규칙을 확정한다.
- [ ] `BTC / XAU / NAS` 자산별 해석 원칙을 문서에 적는다.

## Step 2. 라벨러 입력 규격 확정

- [ ] `ATRP_20`, `ATRP_10`을 정식 helper로 둘지, 초기에는 `regime_volatility_ratio` proxy를 쓸지 결정한다.
- [ ] `B`, `UW`, `LW`, `D`, `Rcur`, `Rmax`, `BullShare`, `C`, `VB`, `VD`, `Hret`, `Lret`, `GF` 공통 변수를 확정한다.
- [ ] `primary + secondary pattern` 구조를 유지한다.

## Step 3. 패턴별 수치 v2 반영

- [ ] `2`, `3`, `14`, `19`를 ATR 정규화 기준으로 바꾼다.
- [ ] `5`는 `H/Lret >= 2 & D >= 0.30` 기준으로 조정한다.
- [ ] `12`, `23`은 압축/재시험 강화 기준으로 유지한다.
- [ ] `15`는 `Rcur >= 5` 또는 `Rcur >= 4 + VB >= 2.0`로 조정한다.
- [ ] `17`은 `VB >= 3.0 + 지속 확인` 기준으로 바꾸고, 초기에는 `낮은 VD` proxy를 허용한다.
- [ ] `1`, `10`, `4`는 기준 유지 또는 소폭 보정으로 둔다.

## Step 4. 검증 전략 고정

- [ ] 1주 데이터 기준으로 `pattern hit-rate`를 확인한다.
- [ ] `false positive`가 많은 패턴과 `too strict`한 패턴을 분리한다.
- [ ] v1 대비 confusion 감소 여부를 비교한다.

## Step 5. 후속 구현 연결

- [ ] compact dataset에 `teacher_pattern_*` 컬럼이 붙을 때 v2 기준을 사용하도록 메모한다.
- [ ] 자동 추천 라벨러를 붙일 경우 v1이 아니라 v2 기준에서 시작하도록 연결한다.
- [ ] execution 룰 보정은 teacher-label hit-rate 검증 후로 미룬다.
