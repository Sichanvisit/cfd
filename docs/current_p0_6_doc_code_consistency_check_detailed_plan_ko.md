# Current P0-6 Doc Code Consistency Check Detailed Plan

## 목표

`P0-6`의 목표는 지금까지 잠근 `P0-1 ~ P0-5` 기준이 실제 코드와 문서에서 서로 충돌하지 않는지 점검하는 것입니다.

이 단계는 새 기능을 만드는 단계가 아니라, 다음 단계로 넘어가기 전에 baseline이 흔들리지 않게 확인하는 감사 단계입니다.

---

## 왜 필요한가

`P0`는 기준면 단계라서, 문서와 코드가 엇갈리면 이후 단계에서 같은 말을 서로 다른 뜻으로 쓰게 됩니다.

대표적으로 막아야 하는 문제는 아래와 같습니다.

- 문서에는 `check topic / report topic`이 분리되어 있는데 코드 baseline은 아직 옛 route를 보는 경우
- status enum 문서는 갱신됐는데 실제 policy contract가 다른 값을 쓰는 경우
- proposal envelope 필수 필드를 문서에 적어놨지만 producer/bridge가 다른 shape를 쓰는 경우
- board field naming 문서는 갱신됐는데 실제 master board가 다른 키를 쓰는 경우
- ownership 문서는 정리됐는데 발송 지점이 다른 route를 계속 쓰는 경우

---

## 이번 단계에서 실제로 하는 일

### 1. baseline consistency audit 추가

파일:

- `backend/services/improvement_baseline_consistency_audit.py`

역할:

- P0 핵심 policy contract version 수집
- P0 필수 문서 존재 여부 확인
- baseline consistency 결과를 PASS/FAIL로 요약
- snapshot export

### 2. snapshot과 테스트 고정

파일:

- `tests/unit/test_improvement_baseline_consistency_audit.py`

artifact:

- `data/analysis/shadow_auto/improvement_baseline_consistency_audit_latest.json`
- `data/analysis/shadow_auto/improvement_baseline_consistency_audit_latest.md`

---

## 완료 조건

- P0 핵심 policy version이 audit payload에 모두 모인다
- P0 필수 문서가 모두 존재하는지 audit에서 확인한다
- audit 결과가 PASS/FAIL로 한눈에 보인다
- snapshot과 테스트가 기준을 고정한다

---

## 이번 단계에서 일부러 하지 않는 것

- 문서 내용 semantic diff 비교
- 런타임 동작 deep inspection
- detector/readiness logic 변경

즉 `P0-6`은 정합성 baseline을 찍는 단계이지, 실제 운영 로직을 다시 손보는 단계는 아닙니다.

---

## 다음 단계 연결

`P0-6`까지 닫히면 `P0`는 기준면으로서 사실상 마감됩니다.

그 다음부터는:

1. `P2 quick 설명력`
2. `P1 readiness surface`

순서로 들어가도, 용어/route/shape/ownership 때문에 다시 흔들릴 가능성이 크게 줄어듭니다.
