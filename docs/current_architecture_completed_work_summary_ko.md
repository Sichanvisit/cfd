# 현재 아키텍처 및 완료 작업 요약

작성일: 2026-04-08 (KST)

## 1. 문서 목적

이 문서는 지금 이 레포가 실제로 어디까지 와 있는지를 한 번에 읽을 수 있도록 정리한 "현재 기준선 문서"다.

중요한 점은 두 가지다.

1. 이 문서는 "원래 설계 의도"보다 "실제로 존재하는 코드/모델/리포트/활성 상태 파일"을 우선한다.
2. "완료"는 단순히 설계 문서가 있는 상태가 아니라, 실제 산출물이나 런타임 연결이 확인되는 상태를 뜻한다.

즉, 이 문서는 아이디어 설명서가 아니라 현재 시스템의 실체를 정리한 운영 요약이다.

---

## 2. 한 줄 요약

이 프로젝트는 더 이상 단순 threshold 기반 진입/청산 봇이 아니다.

현재 구조는 다음이 겹쳐 있는 하이브리드 시스템이다.

- 기존 threshold/score 기반 실전 런타임
- entry/wait/exit를 utility 관점으로 보강한 의사결정 계층
- semantic_v1 학습/예측 계층
- shadow auto 및 bounded candidate 승인/활성화 계층
- state25 후보 자동 승격 및 log-only 결합 계층
- closed trade 기반 profitability operations 분석 계층
- breakout event 보조 축의 초기 골격

즉, "기존 실행 엔진 위에 학습/분석/후보 승격/그림자 실행 계층이 얹혀 있는 상태"로 보는 것이 가장 정확하다.

---

## 3. 가장 먼저 구축되어 지금도 유지되는 기반

초기에 가장 먼저 한 일은, 모든 판단을 한 파일 한 규칙으로 밀어넣는 방식에서 벗어나서 기능 축별로 구조를 나누는 것이었다.

그 결과 현재 기준으로 다음 축이 실제 코드 레벨에서 분리되어 있다.

- 진입 판단 축
- 대기 및 관망 판단 축
- 청산 판단 축
- 리플레이/라벨/학습 데이터 생성 축
- 운영 리포트/분석 산출 축

이 분리는 단순한 파일 분리가 아니라 이후 semantic, shadow, profitability, candidate promotion이 들어올 수 있는 토대를 만든 작업이었다. 지금 시스템이 커졌는데도 무너지지 않은 가장 큰 이유가 이 구조 분해다.

---

## 4. 진입(entry) 축에서 완료된 것

진입 쪽은 이미 "조건 만족하면 들어간다" 수준을 넘어서 있다.

구축 완료된 핵심은 다음과 같다.

- 후보 신호를 stage/guard/context 기준으로 정리하는 경로가 있다.
- 점수 기반 threshold 경로가 여전히 실전 기준선으로 남아 있다.
- 동시에 utility 관점의 진입 통제가 들어가 있다.
- 즉, 단순 score뿐 아니라 확률, 기대 손익 성격의 조합값으로 진입 허용 여부를 보강한다.

이 말은 현재 진입 로직이 완전히 semantic-only는 아니지만, 그렇다고 순수 룰셋도 아니라는 뜻이다.

정확히는 다음과 같이 이해하는 편이 맞다.

- baseline authority는 아직 threshold/score 쪽이 강하다.
- 하지만 그 위에 utility gate와 부가 해석 계층이 이미 들어와 있다.
- 따라서 외부에서 흔히 말하는 "이 시스템은 EV가 전혀 없다"는 평가는 현재 코드와 맞지 않는다.

요약하면 진입은 "기존 실전 규칙 + utility 보강" 상태까지는 이미 완료되었다.

---

## 5. 기다림(wait/hold) 축에서 완료된 것

이 프로젝트가 단순 진입/청산 봇이 아닌 이유 중 하나가 바로 wait 축이다.

현재 wait 축에서 완료된 것은 다음과 같다.

- 진입 직후 바로 손대지 않고 유지/관망/전환을 구분하는 로직이 있다.
- hold, wait, reverse, exit의 후보 행동을 비교하는 기반이 있다.
- 즉, 아무 행동도 하지 않는 선택을 하나의 의사결정으로 다룬다.

이건 매우 중요하다.

보통 단순 자동매매 코드는 "들어감 / 나감"만 생각한다. 하지만 현재 프로젝트는 "지금 아무것도 하지 않는 것이 최선인가"를 별도 상태로 다룰 수 있게 구조가 열려 있다.

나중에 semantic shadow나 state25 후보가 붙을 수 있었던 것도, 이 중간 상태가 이미 구조적으로 존재했기 때문이다.

---

## 6. 청산(exit) 축에서 완료된 것

청산은 초창기보다 훨씬 많이 진화했다.

완료된 핵심은 다음과 같다.

- 청산 판단이 단순 반대 신호 감지에만 묶여 있지 않다.
- exit now / hold / reverse / wait 성격의 비교 경로가 존재한다.
- 청산 학습 데이터도 단순 "가격이 올랐냐/내렸냐"가 아니라, 현재 청산과 계속 보유의 차이를 반영하도록 설계되어 있다.

즉, exit는 이미 "조건이 깨졌으니 무조건 나간다"는 1차원 룰셋에서 벗어났다.

다만 아직 완전히 하나의 경제적 목적함수로 통일되어 있다고 보기는 어렵다.

정확한 평가는 이렇다.

- 청산은 utility/EV-lite 요소를 이미 갖고 있다.
- 하지만 실전 authority가 완전히 그 한 축으로 일원화된 것은 아니다.
- 그래서 외부에서 "청산이 전부 조건 변화 기준"이라고 단정하는 것도 맞지 않고,
- 반대로 "이제 청산이 완전한 경제 최적화 시스템이 되었다"고 말하는 것도 과장이다.

가장 정확한 표현은 "청산은 이미 다축 의사결정 구조로 바뀌었고, 경제적 판단 축도 들어와 있지만, 최상위 단일 기준으로 100% 수렴한 단계는 아니다"다.

---

## 7. 학습 데이터셋, 라벨, 경제적 타깃 축에서 완료된 것

외부에서 이 프로젝트를 잘 모르는 사람이 가장 자주 오해하는 부분이 여기다.

현재 프로젝트는 단순 가격 방향 예측만 하는 구조가 아니다.

이미 완료된 것은 다음과 같다.

- closed trade 기반 데이터셋 생성 경로가 있다.
- entry 쪽에는 수익 여부 기반 라벨링이 이미 존재한다.
- exit 쪽에는 지금 나가는 것과 더 보유하는 것의 차이를 반영한 라벨 설계가 있다.
- outcome label 계층이 별도로 존재한다.
- replay 및 contract 기반 라벨 파생 경로가 있다.
- economic learning target을 계산하는 보조 축이 존재한다.
- `learning_total_label` 같은 총합형 경제 라벨이 실제 서비스 코드에 연결돼 있다.

즉, 현재 프로젝트의 문제를 "라벨을 전혀 돈 기준으로 안 만들고 있다"라고 말하는 건 사실과 다르다.

더 정확한 진단은 다음과 같다.

- 경제적 라벨은 이미 일부 구현되어 있다.
- semantic 계층에서는 여전히 해석 가능한 중간 라벨과 관리 라벨이 함께 쓰인다.
- 따라서 문제의 본질은 "돈 기준 라벨이 전혀 없다"가 아니라,
- "경제적 목적이 시스템 전체 authority로 완전히 통합되진 않았다"에 가깝다.

이 차이는 매우 크다.

전자는 설계를 처음부터 다시 해야 하는 상태고, 후자는 이미 깔아둔 축을 어디까지 주도권으로 끌어올릴지의 문제다.

---

## 8. semantic_v1 및 forecast/bridge 축에서 완료된 것

이제는 semantic 계층도 설계 문서 수준을 넘어 실제 산출물을 가진 상태다.

현재 확인되는 완료 항목은 다음과 같다.

- semantic bridge proxy 데이터셋이 실제로 생성되어 있다.
- `timing_dataset.parquet`
- `entry_quality_dataset.parquet`
- `exit_management_dataset.parquet`
- 해당 데이터셋들의 summary JSON도 함께 생성된다.
- semantic 모델 3종이 실제 파일로 존재한다.
- `timing_model.joblib`
- `entry_quality_model.joblib`
- `exit_management_model.joblib`
- 각 모델별 summary JSON 및 metrics 파일도 생성된다.

즉, semantic은 더 이상 "나중에 붙일 예정인 개념"이 아니다.

이미 다음 단계까지는 완료되었다.

- bridge proxy row 생성
- semantic 학습용 데이터셋 생성
- 모델 학습
- summary/metrics 산출

다만 이 계층의 현재 위치를 정확히 표현하면 다음과 같다.

- semantic 모델은 존재한다.
- semantic shadow와 결합되는 운영 산출도 존재한다.
- 하지만 baseline 실전 authority를 완전히 semantic이 대체한 상태는 아니다.

따라서 semantic 계층은 "없다"가 아니라 "구축 완료 + 부분 운영 + 아직 최상위 authority는 아님" 상태다.

---

## 9. shadow auto 및 semantic shadow 축에서 완료된 것

4월 들어 가장 크게 진척된 부분이 바로 이 축이다.

현재 shadow auto 쪽은 단순 preview를 넘어서 다음 산출물들이 실제로 존재한다.

- shadow dataset bias audit
- shadow divergence audit
- shadow target mapping
- shadow threshold sweep
- shadow correction loop
- shadow vs baseline 비교
- shadow evaluation
- shadow auto decision
- semantic shadow training corpus
- semantic shadow training bridge adapter
- semantic shadow proxy datasets
- semantic shadow preview bundle
- bounded candidate stage/approval
- runtime activation demo
- active runtime activation

특히 중요한 것은 다음 두 상태다.

1. bounded candidate approval 산출물이 실제로 존재한다.
2. active runtime activation manifest와 보고서도 실제로 존재한다.

이건 무슨 뜻이냐면, shadow 계층이 단순 분석 리포트 생산을 넘어서 "후보 승인"과 "활성화 절차"까지 코드와 산출물로 묶였다는 뜻이다.

하지만 여기서 과장하면 안 된다.

현재 확인되는 현실은 다음과 같다.

- semantic shadow 활성화 메커니즘은 있다.
- 강제 활성화 데모/manifest도 있다.
- 하지만 보고서에는 여전히 `semantic_live_mode: disabled`가 보인다.
- 별도 baseline acceptance 문서에는 `semantic_live_mode: threshold_only`가 남아 있다.

즉, shadow/semantic은 이제 장식이 아니라 운영 후보 계층이 맞다.

그러나 아직 실전 baseline을 완전히 덮어쓴 지배적 권한층은 아니다.

가장 정확한 표현은 "활성화 체계까지 구현된 후보 운영 계층"이다.

---

## 10. profitability operations 축에서 완료된 것

3월 말 이후 이 축은 더 이상 roadmap가 아니라 실제 분석 생산 라인으로 봐야 한다.

현재 다음 단계들이 모두 산출물로 존재한다.

- P1 lifecycle
- P2 expectancy
- P2 zero-pnl gap audit
- P3 anomaly
- P4 compare
- P5 casebook
- P6 health
- P7 counterfactual
- P7 guarded size overlay
- P7 guarded size overlay dry run

이 축의 의미는 매우 크다.

이제 프로젝트는 단순히 "모델을 돌린다"에서 끝나지 않는다.

이미 다음 질문에 답할 수 있는 분석 체계를 갖췄다.

- 실제 closed trade 기준 expectancy는 어떤가
- zero pnl이나 attribution gap은 어디서 생기나
- 어떤 케이스가 반복적으로 나쁜가
- 사이즈 오버레이를 얹으면 결과가 어떻게 바뀌나
- 건강도와 이상 징후는 무엇인가

즉, 운영 실패를 감으로 말하는 단계는 지나갔다.

아직 개선할 부분은 남아 있지만, "분석 프레임이 없다"는 말은 더 이상 맞지 않는다.

---

## 11. state25 candidate 자동 승격 및 live 결합 축에서 완료된 것

이 부분도 현재는 실제 상태 파일이 존재한다.

확인되는 완료 항목은 다음과 같다.

- candidate run 보고서
- gate 보고서
- execution policy integration 보고서
- execution policy log-only binding 보고서
- auto promote live actuator 보고서
- active candidate state 파일
- auto promote history 로그

가장 중요한 현재 상태는 이렇다.

- active candidate가 실제로 존재한다.
- policy source는 `state25_candidate`다.
- rollout phase는 `log_only`다.
- binding mode도 `log_only`다.

즉, state25 후보는 이제 "문서상 개념"이 아니라, 실제로 선택되고 바인딩 모드가 기록되는 운영 객체다.

다만 아직 실거래 주 권한으로 승격된 것은 아니고, 현재 확인되는 수준은 log-only 결합이다.

이 표현이 중요하다.

- "아무것도 안 됐다"도 아니고,
- "실전 authority로 완전히 올라갔다"도 아니다.

정확히는 "후보 선발, 승격 이력, log-only 바인딩까지 운영 루프가 만들어진 상태"다.

---

## 12. product acceptance 및 기준선 동결 축에서 완료된 것

현재 프로젝트에는 product acceptance 기준선 문서도 존재한다.

여기서 확인되는 핵심은 다음이다.

- baseline freeze 문서가 있다.
- tri-symbol 기준으로 최근 row와 display 상태를 점검한다.
- must-show missing, must-hide leakage, bad exit candidate, divergence seed 같은 운영 체크 항목이 있다.
- 해당 기준선 문서에는 `semantic_live_mode: threshold_only`가 명시되어 있다.

이 문서의 의미는 단순 보고가 아니다.

이건 지금 시스템의 "공식 baseline authority가 어디에 있는가"를 보여주는 기준점이다.

즉, semantic/shadow/state25가 많이 진척되었더라도, baseline acceptance 관점에서는 아직 threshold-only가 기본선이라는 뜻이다.

이 사실은 현재 구조를 이해할 때 반드시 함께 봐야 한다.

---

## 13. breakout event 축에서 완료된 것

breakout 계열은 아직 완성된 실전 축은 아니지만, 골격 정리는 상당히 진행되었다.

현재 확인되는 완료 항목은 다음과 같다.

- breakout event runtime contract 정리
- overlay candidate/trace contract 정리
- manual alignment contract 정리
- replay action target contract 정리
- phase0 interface freeze 보고서
- manual alignment / overlap recovery / learning bridge / backfill scaffold 계열 산출물

현재 단계 판정은 다음과 같다.

- `P0 interface_freeze`는 ready
- `P1 detect_only_runtime_injection`은 next
- `P2 manual_alignment_and_shadow_preview`도 next

따라서 breakout 축은 "초기 골격과 리플레이/보조 분석 준비는 됐지만, 실전 detect-only 런타임 주입은 아직 다음 단계"라고 보는 것이 맞다.

---

## 14. 운영 문서와 읽기 경로에서 완료된 것

현재 이 프로젝트는 기능 자체만 있는 것이 아니라, 읽어야 할 운영 문서 계층도 상당 부분 정리되어 있다.

이미 존재하는 대표 문서 축은 다음과 같다.

- 현재 아키텍처 요약 문서
- shadow auto 시스템 설계 문서
- profitability operations 로드맵 및 실제 산출물
- economic learning target 로드맵
- state25 auto promote / live actuator 설계 문서
- forecast-state25 learning bridge 설계 문서
- breakout event 관련 단계 문서

이 말은 곧, 이제 프로젝트를 이해하는 방식이 단순 코드 grep만이 아니라는 뜻이다.

현재는 다음 세 층을 함께 읽어야 전체가 보인다.

- 서비스 코드
- 생성된 모델/데이터셋/상태 파일
- 분석 및 운영 문서

즉, 이 프로젝트는 이미 "코드만 읽어서는 다 안 보이는 단계"에 들어와 있다.

---

## 15. 현재 시스템을 객관적으로 평가하면

현재 상태를 가장 정확하게 표현하면 다음과 같다.

### 이미 확실히 완료된 것

- entry / wait / exit 구조 분해
- utility 보강 진입/청산 판단
- closed trade 기반 학습/라벨 파생 축
- economic target 보조 라벨 축
- semantic_v1 bridge dataset 생성
- semantic_v1 모델 학습 및 summary/metrics 산출
- shadow auto 분석 파이프라인
- bounded candidate 승인 산출
- runtime activation manifest/보고서
- profitability operations P1~P7
- state25 candidate log-only 바인딩
- product acceptance baseline freeze

### 부분 완료 또는 운영 후보 상태인 것

- semantic의 실전 authority 승격
- shadow의 실시간 성과 검증
- state25 후보의 log-only 이후 단계
- breakout detect-only 런타임 주입

### 아직 남아 있는 본질 과제

- baseline threshold authority와 semantic/economic authority를 어디까지 통합할지 결정
- zero-pnl, attribution gap, information gap 정리
- discriminative edge를 실제 운영 성과로 입증
- shadow와 bounded candidate를 실전 안전장치와 함께 승격할지 검증
- 경제적 목적함수를 라이브 의사결정 최상단으로 얼마나 끌어올릴지 정리

즉, 지금 남은 과제는 "아무것도 없는 상태에서 처음 설계하기"가 아니다.

이미 너무 많은 것이 구축되어 있어서, 앞으로의 핵심은 새 기능을 무작정 더하는 것이 아니라 다음을 정리하는 데 있다.

- 어떤 계층이 최종 authority인가
- 어떤 계층은 log-only/analysis-only인가
- 무엇을 promotion gate로 삼을 것인가
- 어떤 경제적 지표를 실전 승격 조건으로 인정할 것인가

---

## 16. 결론

현재 프로젝트는 다음처럼 요약하는 것이 가장 정확하다.

"기존 threshold 기반 실전 엔진 위에, utility/semantic/shadow/profitability/state25 후보 승격 계층이 실제 산출물과 함께 얹혀 있는 하이브리드 트레이딩 시스템"

여기서 중요한 판단은 두 가지다.

1. 이 프로젝트는 생각보다 훨씬 많이 완성되어 있다.
2. 동시에 아직 하나의 권위 있는 라이브 판단 축으로 완전히 수렴되지는 않았다.

따라서 현재 단계의 핵심은 "새로운 개념을 계속 추가하는 것"보다 다음을 명확히 하는 것이다.

- baseline authority
- semantic/shadow 후보의 승격 조건
- economic target의 최상위 의사결정 반영 범위
- log-only와 live 적용의 경계

한마디로 정리하면,

이 시스템은 미완성 초기 프로토타입이 아니라, 이미 여러 계층이 완성된 중대형 운영 후보 시스템이다.

다만 지금부터의 진짜 난제는 기능 추가보다 "권한 통합과 승격 기준 정리"에 있다.
