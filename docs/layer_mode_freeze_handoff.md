# Layer Mode Freeze / Handoff

`layer_mode_freeze_handoff_v1` closes Layer Mode as an always-on policy overlay handoff.

## Completion Criteria

- all semantic layers always compute
- mode changes only influence strength
- raw and effective payloads remain dual-written
- policy overlay sits above consumer handoff and below execution
- `Energy` may be redefined later as a utility or compression helper, not as an independent semantic meaning layer

## Official Helper

`resolve_layer_mode_handoff_payload(...)` is the canonical handoff resolver.

It returns the raw semantic field map, effective field map, policy overlay payload, logging replay payload, the consumer policy bridge, and the allowed future role for `Energy`.
