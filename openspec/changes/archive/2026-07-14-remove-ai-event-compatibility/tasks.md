# Tasks

- [x] Define the end of the AIEvent compatibility period in this change.
- [x] Update event and AI reporting spec deltas to make Event the only formal model.
- [x] Add a local development data spec delta.
- [x] Remove AIEvent application code and compatibility response fields.
- [x] Collapse Alert relations to `Alert.event -> events.Event`.
- [x] Add a forward-only migration that preserves formal Event linkage for old alerts before deleting AIEvent.
- [x] Add the formal event list endpoint and tests.
- [x] Add idempotent `seed_dev_data` data without AIEvent.
- [x] Document local development database initialization and reset.
- [x] Run OpenSpec and Django validation commands.
