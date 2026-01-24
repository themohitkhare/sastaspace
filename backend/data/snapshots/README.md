# Game Snapshots Directory

This directory contains game state snapshots captured when invariant violations are detected.

## Snapshot Format

Snapshots are saved as JSON files with the following naming convention:

```
bug_<game_id_8chars>_<timestamp>.json
```

## Snapshot Contents

Each snapshot includes:

- **timestamp**: When the snapshot was captured
- **game_id**: Full game ID
- **game_state**: Complete serialized game state
- **action_history**: List of actions leading to the bug
- **chaos_config**: Chaos testing configuration (if applicable)
- **error**: Error message
- **invariant_violations**: List of detected violations

## Usage

### View a Snapshot

```bash
cat bug_abc12345_1234567890.json | jq
```

### List Recent Snapshots

```bash
ls -lt bug_*.json | head -10
```

### Replay a Snapshot

```python
from app.modules.sastadice.services.snapshot_manager import SnapshotManager

snapshot_mgr = SnapshotManager(repository)
game = await snapshot_mgr.replay("path/to/snapshot.json")
```

## Cleanup

Snapshots can accumulate over time. Consider:

1. **Archiving old snapshots** - Move resolved bugs to archive/
2. **Deleting duplicates** - Remove snapshots of fixed bugs
3. **Compressing** - Compress old snapshots to save space

```bash
# Archive snapshots older than 30 days
find . -name "bug_*.json" -mtime +30 -exec mv {} archive/ \;

# Compress archived snapshots
cd archive && gzip *.json
```

## Best Practices

1. **Don't delete snapshots immediately** - They help identify patterns
2. **Create test cases from snapshots** - Add regression tests
3. **Share snapshots in bug reports** - Include snapshot path
4. **Review snapshots regularly** - Look for common failure modes

## Gitignore

This directory is typically ignored in version control, but specific snapshots
can be committed for regression testing purposes.
