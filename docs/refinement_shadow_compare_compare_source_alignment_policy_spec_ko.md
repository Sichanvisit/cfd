# Shadow Compare Compare Source Alignment Policy Spec

## 1. 목적

이 문서는 shadow compare 품질개선 트랙에서
`compare source alignment policy`를 고정하는 전용 spec이다.

현재 핵심 병목은:

- live `entry_decisions.csv`는 계속 최신화되는데
- shadow compare가 읽는 replay source는
  - production replay
  - audit replay
  - legacy replay
  가 섞여 있고
- compare window도 source coverage와 따로 놀아서
  `missing_replay_join`가 거의 전부를 차지한다는 점이다.

따라서 이 문서의 목적은

- 어떤 replay source를 compare에 써야 하는지
- 어떤 source는 compare에서 제외해야 하는지
- entry row와 replay row의 시간 범위를 어떻게 맞출지

를 먼저 정책으로 잠그는 것이다.

## 2. 현재 문제 요약

기준 문서:

- [refinement_shadow_compare_replay_join_alignment_audit_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_replay_join_alignment_audit_ko.md)
- [refinement_shadow_compare_quality_baseline_snapshot_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_quality_baseline_snapshot_ko.md)

현재 latest report에서 드러난 핵심은 아래와 같다.

- `shadow_available_rows = 22839`
- `matched_replay_rows = 310`
- `missing_replay_join_rows = 22529`
- `scorable_shadow_rows = 0`

원인 해석:

1. compare source가 현재 live row 범위를 충분히 덮지 못한다
2. source 안에 audit/test용 replay가 섞여 있다
3. 현재 compare는 "어떤 replay를 compare 대상으로 인정할지" 정책이 없다

## 3. 이 문서가 하는 일

이 문서는 아래를 고정한다.

- compare source의 분류 체계
- source 선택 기준
- source 제외 기준
- time window alignment 기준
- report에서 보여줘야 할 source scope 정보
- 다음 구현 순서

## 4. source 분류

shadow compare에서 replay source는 아래 세 종류로 나눈다.

### 4-1. production compare source

목적:

- current live `entry_decisions.csv`와 실제로 비교 가능한 replay source

특징:

- production runtime / replay intermediate에서 나온 파일
- compare 가능한 label 품질을 기대하는 source
- audit/test용 synthetic replay가 아님

### 4-2. audit / test source

목적:

- R2 audit, casebook, test, sample export 검증용

예시:

- `replay_dataset_rows_r2_audit.jsonl`
- `replay_dataset_rows_r2_audit_entered.jsonl`

정책:

- default production compare source에서 제외한다

### 4-3. legacy / snapshot source

목적:

- preview build용 과거 기준 snapshot

예시:

- `replay_intermediate_legacy_*`
- 특정 preview build와 짝지어진 replay rows

정책:

- explicit preview audit에는 쓸 수 있으나
- current live shadow compare default source로는 쓰지 않는다

## 5. source 선택 원칙

### 원칙 A. compare source는 기본적으로 explicit여야 한다

가능하면 아래 둘 중 하나로 간다.

1. 명시적 디렉터리 지정
2. latest production source manifest 기반 선택

즉 `data/datasets/replay_intermediate` 전체를 무조건 다 긁는 방식은
이제 default로 두지 않는 것이 맞다.

### 원칙 B. audit/test source는 default에서 제외한다

최소한 이름 기준으로 아래는 exclude 후보다.

- `*r2_audit*`
- `*smoke*`
- `*tail300*`
- `*tail3000*`
- `*legacy*`

주의:

- 이것은 최종 구현에서 이름 규칙만으로 끝낼지
- manifest/type marker까지 볼지는 checklist 단계에서 결정한다.

### 원칙 C. compare window는 replay coverage를 넘지 않게 맞춘다

현재 compare는 current live row 전체를 보지만,
replay source는 그 전체를 커버하지 못하는 경우가 많다.

따라서 compare는 최소한 아래 둘 중 하나여야 한다.

1. replay source latest coverage 기준으로 live row를 잘라서 비교
2. source manifest가 가진 anchor range 기준으로 live row를 제한

### 원칙 D. source scope mismatch는 report에서 blocker-level로 보여야 한다

단순 warning이 아니라, 다음이 직접 보이게 해야 한다.

- entry range
- replay source range
- source file list
- excluded file list
- coverage mismatch reason

## 6. compare source policy 방향

## 6-1. 권장 baseline

권장 baseline은 아래다.

- shadow compare default source는 `production compare source`만 사용
- audit/test/legacy source는 명시적으로만 허용
- compare 대상 live row는 replay source coverage 안으로 제한

## 6-2. 이름 규칙만으로 끝내지 않는다

파일명 exclude는 빠른 방어에는 좋지만,
장기적으로는 source metadata가 더 필요하다.

권장 방향:

- source manifest 또는 source class marker 추가 검토
- 최소한 report에는 어떤 파일이 선택/제외됐는지 남김

## 6-3. preview audit과 current live compare는 분리한다

preview audit은 explicit preview pair를 유지해도 된다.

하지만 current live shadow compare는
preview replay source를 default로 재사용하면 안 된다.

즉:

- preview 평가용 source
- current live compare용 source

를 정책상 분리해야 한다.

## 7. 직접 owner

### 1차 owner

- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)

### 2차 owner

- [replay_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\offline\replay_dataset_builder.py)
- source manifest를 쓴다면 관련 export/manifest writer

### 간접 owner

- [run_semantic_v1_preview_audit.py](c:\Users\bhs33\Desktop\project\cfd\scripts\run_semantic_v1_preview_audit.py)

## 8. 이번 정책에서 하지 않을 것

- timing / entry_quality / exit target 조정
- split health threshold 변경
- chart/runtime execution rule 변경
- live rollout mode 변경

## 9. 권장 구현 순서

### Phase A. Source Inventory

목표:

- 현재 replay source 디렉터리 안의 파일을 production / audit / legacy로 분류한다

### Phase B. Source Selection Contract

목표:

- default compare source selection 규칙을 코드와 문서로 고정한다

### Phase C. Time Window Alignment

목표:

- entry row를 replay coverage 안으로 제한하는 규칙을 넣는다

### Phase D. Report Surface

목표:

- selected / excluded source file list
- entry/replay range
- mismatch reason

을 report에 같이 남긴다

## 10. 완료 기준

아래를 만족하면 이 정책 단계를 닫는다.

- current live shadow compare에서 audit/test source가 기본 compare source에 섞이지 않는다
- compare window가 replay coverage와 맞는다
- report만 봐도 어떤 source가 선택/제외됐는지 보인다
- `missing_replay_join`의 구조적 원인이 source scope mismatch인지 아닌지 더 분명해진다

## 11. 다음 단계

이 spec 다음에는 implementation checklist를 만들고,
그 다음 실제 구현은

1. source inventory / exclusion
2. compare source selection
3. time alignment
4. report surface

순으로 들어간다.
