# Shadow Compare Compare Source Alignment Policy Implementation Checklist

## 1. 목적

이 문서는 [refinement_shadow_compare_compare_source_alignment_policy_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_compare_source_alignment_policy_spec_ko.md) 실행 checklist다.

목표는 shadow compare가 현재 live row와 맞는 replay source만 보게 하고,
audit/test/legacy source가 default compare에 섞이지 않게 만드는 것이다.

## 2. 이번 단계에서 할 것 / 하지 않을 것

### 할 것

- source inventory 정리
- exclude / include 정책 고정
- default compare source selection 구현
- time window alignment 구현
- selected / excluded source scope report surface
- 테스트와 실제 report 재확인

### 하지 않을 것

- target fold 조정
- split health 정책 조정
- promotion threshold 조정
- runtime execution rule 조정

## 3. 입력 기준

기준 문서:

- [refinement_shadow_compare_compare_source_alignment_policy_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_compare_source_alignment_policy_spec_ko.md)
- [refinement_shadow_compare_replay_join_alignment_audit_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_replay_join_alignment_audit_ko.md)

중요 파일:

- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)
- [replay_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\offline\replay_dataset_builder.py)

## 4. 구현 순서

### Step 1. Source Inventory Snapshot

목표:

- replay source 후보 파일들을 production / audit / legacy 관점에서 정리한다

완료 기준:

- baseline inventory memo가 있다

### Step 2. Source Classification Policy 고정

목표:

- 어떤 파일을 default compare source에 포함/제외할지 규칙을 고정한다

예시:

- include: production replay rows
- exclude: `*r2_audit*`, `*smoke*`, `*tail300*`, `*tail3000*`, `*legacy*`

완료 기준:

- classification rule이 문서와 코드에서 같이 읽힌다

### Step 3. Default Source Selection 구현

목표:

- shadow compare default source가 전체 디렉터리를 무조건 다 읽지 않게 만든다

완료 기준:

- selected replay files와 excluded replay files가 정해진다

### Step 4. Time Window Alignment 구현

목표:

- current live entry row를 replay source coverage 안으로 제한한다

완료 기준:

- compare 대상 row가 replay coverage를 넘지 않는다

### Step 5. Report Surface 보강

목표:

- report에서 아래가 바로 보이게 한다

- selected source files
- excluded source files
- entry time range
- replay coverage range
- source mismatch reason

완료 기준:

- report 한 장으로 source alignment 상태를 설명할 수 있다

### Step 6. 테스트 보강

최소 대상:

- source exclusion 회귀
- explicit source override 회귀
- time alignment 회귀

완료 기준:

- 정책이 테스트로 고정된다

### Step 7. 실제 report 재생성

목표:

- current live 기준으로 latest shadow compare를 다시 만들고
- `missing_replay_join`가 구조적으로 줄었는지 확인한다

완료 기준:

- 개선 또는 설명 가능한 잔여 문제가 확인된다

### Step 8. 문서 동기화

목표:

- inventory memo / reconfirm memo / master checklist를 맞춘다

## 5. Done Definition

아래를 만족하면 이 정책 구현 단계를 닫는다.

- default compare source가 production용으로 좁혀진다
- audit/test/legacy source가 default compare에서 빠진다
- compare window가 replay source coverage와 맞는다
- source selection 결과가 report에 보인다
- 실제 report에서 `missing_replay_join`가 줄거나, 남아도 원인이 더 설명 가능해진다
