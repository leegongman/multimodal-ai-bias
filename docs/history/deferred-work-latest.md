# Deferred Work

## Deferred from: code review of 2-7-implement-reasoner-v3-option-index-contract (2026-06-20)

- Replace dummy stage routing based on arbitrary prompt substring detection with an explicit trusted generation-stage contract. Pre-existing behavior in `src/multimodal_bias/models/dummy.py`.
- Harden submission publication against concurrent same-inode mutation by locking immutable staged inputs or validating content identity around publication. Pre-existing behavior in `src/multimodal_bias/submission.py`.
