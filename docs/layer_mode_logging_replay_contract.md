# Layer Mode Logging / Replay Contract

`layer_mode_logging_replay_contract_v1` freezes the replayable audit payload for Layer Mode.

## Canonical Output

- `layer_mode_logging_replay_v1`

## Required Fields

- `configured_modes`
- `raw_result_fields`
- `effective_result_fields`
- `applied_adjustments`
- `block_suppress_reasons`
- `final_consumer_action`

## Goal

One decision row should be enough to replay:

- which modes were configured by layer
- which raw fields and effective fields were relevant
- which policy adjustments were active
- which suppress or block reasons were present
- what final consumer action was taken

## Bridge Rule

The current bridge may still emit empty policy suppressions or hard blocks.
That is valid as long as the payload clearly shows the configured modes, applied adjustments, and final consumer action.
