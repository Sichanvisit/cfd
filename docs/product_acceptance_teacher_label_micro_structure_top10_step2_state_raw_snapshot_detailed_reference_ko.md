# Teacher-Label Micro-Structure Top10 Step 2 state_raw_snapshot 상세 기준서

## 목적

이 문서는 `Step 2. state_raw_snapshot 편입`의 상세 기준서다.

Step 2의 목적은 Step 1에서 만든 `micro_structure_v1` compact helper를
raw state contract에 정식 편입하는 것이다.

이 단계에서 중요한 점은 새 계산을 늘리는 것이 아니라,
이미 계산된 `micro_structure_v1`를:

- `StateRawSnapshot` canonical field
- `raw.metadata` human-readable flat surface

두 층에 동시에 올리는 것이다.

## Step 2 owner

- [models.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/models.py)
- [builder.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/builder.py)
- [test_state_contract.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_state_contract.py)

## 입력

Step 2 입력은 `ctx.metadata["micro_structure_v1"]`다.

권장 shape:

```python
{
    "version": "micro_structure_v1",
    "data_state": "READY",
    "anchor_state": "READY",
    "lookback_bars": 20,
    "baseline_lookback_bars": 50,
    "window_size": 20,
    "volume_source": "tick_volume",
    "body_size_pct_20": 0.18,
    "upper_wick_ratio_20": 0.22,
    "lower_wick_ratio_20": 0.11,
    "doji_ratio_20": 0.15,
    "same_color_run_current": 4,
    "same_color_run_max_20": 7,
    "bull_ratio_20": 0.65,
    "bear_ratio_20": 0.35,
    "direction_run_stats": {...},
    "range_compression_ratio_20": 0.44,
    "volume_burst_ratio_20": 1.90,
    "volume_burst_decay_20": 0.48,
    "swing_high_retest_count_20": 2,
    "swing_low_retest_count_20": 1,
    "gap_fill_progress": 0.72,
}
```

## 정식 편입 필드

Step 2에서 `StateRawSnapshot`로 승격할 필드는 아래와 같다.

- `s_body_size_pct_20`
- `s_upper_wick_ratio_20`
- `s_lower_wick_ratio_20`
- `s_doji_ratio_20`
- `s_same_color_run_current`
- `s_same_color_run_max_20`
- `s_bull_ratio_20`
- `s_bear_ratio_20`
- `s_range_compression_ratio_20`
- `s_volume_burst_ratio_20`
- `s_volume_burst_decay_20`
- `s_swing_high_retest_count_20`
- `s_swing_low_retest_count_20`
- `s_gap_fill_progress`

## 기존 raw field와의 관계

Step 2는 기존 raw field를 대체하지 않는다.

계속 병존하는 기존 field:

- `s_recent_range_mean`
- `s_recent_body_mean`
- `s_session_box_height_ratio`
- `s_session_expansion_progress`
- `s_session_position_bias`
- `s_compression`
- `s_expansion`

즉 이번 단계는 기존 state를 깨는 작업이 아니라,
teacher-state 친화적인 micro-structure 층을 raw contract에 추가하는 단계다.

## fallback 규칙

### 1. micro_structure_v1가 없을 때

- 런타임을 깨지 않는다
- 새 field는 `0.0` 또는 `None`
- metadata에는 `micro_structure_data_state="MISSING"`을 남긴다

### 2. direction_run_stats가 nested에만 있을 때

- top-level 우선
- 없으면 nested `direction_run_stats` fallback 사용

### 3. range compression이 비어 있을 때

- `position_scale.compression_score`를 1차 fallback으로 쓴다

### 4. body size가 비어 있을 때

- 기존 `recent_body_mean`을 1차 fallback으로 쓴다

### 5. gap fill이 없을 때

- `s_gap_fill_progress = None`
- `micro_structure_anchor_state` metadata를 그대로 보존한다

## metadata surface 규칙

raw metadata에는 아래 키를 같이 남긴다.

- `micro_structure_v1`
- `micro_structure_version`
- `micro_structure_data_state`
- `micro_structure_anchor_state`
- `micro_structure_lookback_bars`
- `micro_structure_baseline_lookback_bars`
- `micro_structure_window_size`
- `micro_structure_volume_source`
- `micro_body_size_pct_20`
- `micro_upper_wick_ratio_20`
- `micro_lower_wick_ratio_20`
- `micro_doji_ratio_20`
- `micro_same_color_run_current`
- `micro_same_color_run_max_20`
- `micro_bull_ratio_20`
- `micro_bear_ratio_20`
- `micro_direction_run_stats_v1`
- `micro_range_compression_ratio_20`
- `micro_volume_burst_ratio_20`
- `micro_volume_burst_decay_20`
- `micro_swing_high_retest_count_20`
- `micro_swing_low_retest_count_20`
- `micro_gap_fill_progress`

## Step 2 완료 기준

아래를 만족하면 Step 2 완료로 본다.

1. `StateRawSnapshot`가 새 micro-structure canonical field를 가진다
2. `build_state_raw_snapshot(ctx)`가 `metadata["micro_structure_v1"]`를 정식 승격한다
3. `micro_structure_v1`가 없을 때도 안전하게 fallback된다
4. `test_state_contract.py`에서 raw contract 회귀가 잠긴다
