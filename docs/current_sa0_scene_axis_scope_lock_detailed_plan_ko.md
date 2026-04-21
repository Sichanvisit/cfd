# Current SA0 Scene Axis Scope Lock Detailed Plan

## 목적

이 문서는 `SA0 Scene Axis Scope Lock`을
실제로 어떻게 끝낼지에 대한 상세 구현 로드맵 문서다.

아주 쉽게 말하면,
이 단계의 목적은 "scene을 잘 맞히는 것"이 아니다.
오히려 그 반대다.

> scene을 붙이기 전에
> 무엇이 진짜 scene이고,
> 무엇이 gate이고,
> 무엇이 modifier인지,
> 그리고 어떤 경우에는 action을 흔들지 말아야 하는지를
> 먼저 문서와 코드 기준으로 잠그는 것

즉 SA0는
기능 구현 단계가 아니라
`기준 정의 단계`다.

관련 문서:

- [current_sa0_scene_axis_baseline_matrix_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_sa0_scene_axis_baseline_matrix_v1_ko.md)
- [current_checkpoint_scene_axis_scope_lock_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_scope_lock_v1_ko.md)
- [current_checkpoint_scene_axis_design_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_design_v1_ko.md)

---

## 1. SA0의 결과물은 무엇이어야 하나

SA0가 끝났다고 말하려면
아래 5개가 있어야 한다.

1. `baseline matrix`
   - scene / gate / modifier / maturity / alignment / transition 기준표
2. `scope lock`
   - 어떤 조언을 채택했고 어떤 것은 뒤로 미뤘는지
3. `shared contract`
   - 코드에서 공통으로 참조할 상수와 기본값
4. `reading order`
   - 새로 들어온 사람이 어떤 순서로 문서를 볼지
5. `handoff rule`
   - SA1, SA2에서 무엇을 해도 되고 무엇을 하면 안 되는지

---

## 2. SA0에서 잠가야 하는 것

### 2-1. 축 경계

아래 경계는 무조건 잠근다.

- `surface`
- `checkpoint_type`
- `scene`
- `gate`
- `modifier`
- `action`
- `outcome`

핵심 원칙:

- `checkpoint_type`은 위치 축
- `scene`은 장면 축
- `action`은 행동 축

이 셋은 같은 라벨을 공유하지 않는다.

### 2-2. scene이 action을 직접 지배하지 못한다

반드시 잠근다.

즉:

- `trend_exhaustion -> PARTIAL_THEN_HOLD`를 강하게 밀 수는 있어도
- scene 혼자서 최종 action을 확정하지는 못한다

최종 구조:

```text
scene -> hint / bias
score -> 경쟁
gate -> 억제
resolver -> 최종 action
```

### 2-3. gate는 별도 축이다

`low_edge_state`, `dead_leg_wait`, `ambiguous_structure`는
fine scene이 아니라 gate다.

### 2-4. modifier는 독립 scene으로 커지지 않는다

예:

- `reclaim`
- `thesis_void`
- `fvg_overlap`
- `orderblock_overlap`

은 독립 scene이 아니라 modifier다.

### 2-5. maturity와 confidence는 action 안정화 장치다

이 둘은 단순 기록용이 아니라
action 흔들림을 막는 장치다.

- `runtime_scene_confidence_band`
- `runtime_scene_maturity`

특히 핵심 원칙:

> `probable` 이상이 되어야 scene bias를 본격 반영하고,
> `provisional`에서는 기존 action을 최대한 유지한다.

---

## 3. SA0에서 실제로 해야 하는 작업

### 3-1. baseline matrix 고정

문서:
[current_sa0_scene_axis_baseline_matrix_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_sa0_scene_axis_baseline_matrix_v1_ko.md)

이 문서에서 고정해야 할 것:

- independent scene 목록
- gate 목록
- modifier 목록
- maturity 표
- confidence band 표
- action bias strength 표
- alignment 표
- transition pair 표

### 3-2. scope lock 고정

문서:
[current_checkpoint_scene_axis_scope_lock_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_scope_lock_v1_ko.md)

여기서 고정해야 할 것:

- 이번 조언 중 바로 채택할 것
- 이번 v1에서 아직 보류할 것
- SA2.5 sanity check를 중간에 둔다는 원칙

### 3-3. shared contract 만들기

파일:
[path_checkpoint_scene_contract.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scene_contract.py)

이 파일에서 잠가야 할 것:

- canonical constants
- runtime scene columns
- default payload

즉 코드도 문서와 같은 말을 하게 만든다.

### 3-4. SA1 handoff 조건 고정

SA1로 넘어가도 되는 조건:

- independent scene / gate / modifier가 문서로 잠겨 있음
- 기본 runtime columns가 잠겨 있음
- default scene payload가 코드 contract에 있음
- maturity / alignment / gate block level 규칙이 잠겨 있음

---

## 4. 이번 SA0에서 나온 코드 레벨 토대

이번 SA0 기준에서 코드 토대로 보는 파일은 아래다.

- [path_checkpoint_scene_contract.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scene_contract.py)

이 파일의 역할은 아주 단순하다.

- scene 상수의 single source of truth
- 기본 scene payload의 single source of truth

즉 앞으로 SA1, SA2, SA3이
각자 자기 기준으로 scene 이름을 만들지 못하게 막는다.

---

## 5. 검증 포인트

SA0는 기능 테스트보다
기준 일치 테스트가 중요하다.

### 5-1. 문서 검증

- direction 문서와 scope-lock 문서가 충돌하지 않는가
- baseline matrix와 scope-lock이 같은 scene 이름을 쓰는가
- gate, maturity, alignment 기준이 일치하는가

### 5-2. 코드 검증

- shared contract가 존재하는가
- scene 기본 컬럼과 기본값이 한 군데에서 정의되는가
- 기존 SA1 코드가 그 contract를 참조하는가

### 5-3. 테스트 검증

- contract unit test가 존재하는가
- 기본 payload가 기대값을 반환하는가
- 허용되지 않은 key가 기본 payload에 섞이지 않는가

---

## 6. 완료 기준

SA0가 완료됐다고 보려면 아래를 만족해야 한다.

- baseline matrix 문서가 존재
- scope-lock 문서가 존재
- shared contract 코드가 존재
- contract unit test가 통과
- SA1에서 쓸 scene 컬럼과 기본값이 코드/문서 기준으로 일치

즉 SA0 완료는
"뭔가 구현됐다"가 아니라
"이제부터는 같은 말을 하게 된다"에 가깝다.

---

## 7. SA1로 넘기는 기준

SA1은 이 토대 위에서
실제로 checkpoint row에 scene 컬럼을 여는 단계다.

그러므로 SA0에서 SA1로 넘길 때
아래가 이미 잠겨 있어야 한다.

- independent scene 사전
- gate 사전
- modifier 사전
- maturity 규칙
- confidence band 규칙
- alignment 규칙
- gate block level 규칙
- transition 기본 필드

이게 잠기지 않으면
SA1은 컬럼을 만들어도 곧 다시 바뀌게 된다.

---

## 8. 다음 단계

SA0 이후 바로 이어지는 단계는 `SA1 Scene Schema Extension`이다.

관련 문서:

- [current_sa1_scene_schema_extension_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_sa1_scene_schema_extension_detailed_plan_ko.md)

즉 지금 순서는 아래처럼 보는 게 맞다.

1. `SA0`
   - 무엇을 말할지 잠금
2. `SA1`
   - 그 말을 담을 칸 만들기
3. `SA2`
   - 그 칸에 heuristic scene seed 넣기

---

## 9. 아주 짧은 결론

SA0의 본질은 이거다.

> scene axis를 붙이기 전에,
> 앞으로 모두가 같은 단어와 같은 규칙을 쓰게 만드는 것

이 단계가 단단할수록
그 다음 구현은 덜 흔들린다.
