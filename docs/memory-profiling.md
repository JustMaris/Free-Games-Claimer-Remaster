# Memory Profiling Commands for Free-Games-Claimer-Remaster

## Overview
These commands help identify memory usage and potential optimization opportunities in the Free-Games-Claimer-Remaster application.

---

## 1. Python Object Memory Profiling

### Check what objects consume memory
```bash
kubectl -n free-games-claimer exec free-games-claimer-XXXX-XXXX -- python3 -c "
from pympler import tracker, muppy, summary
import gc

# Track allocations over time
tr = tracker.SummaryTracker()
gc.collect()
tr.print_diff()  # Show memory changes

# Or: dump all objects by type
all_objects = muppy.get_objects()
sum1 = summary.summarize(all_objects)
summary.print_(sum1)
"
```

**Install first:** `pip install pympler memory_profiler`

**Look for:**
- Large dictionaries/lists that aren't needed
- Cached data that grows unbounded
- SQLAlchemy session objects
- Playwright context references

---

## 2. Chromium Process Memory

### Check Chrome/Chromium processes while claiming
```bash
kubectl -n free-games-claimer exec free-games-claimer-XXXX-XXXX -- ps aux | grep -E 'chrome|chromium'
```

**Look for:**
- Multiple Chromium processes (should be cleaned up after each store)
- Orphaned processes (our `_sweep_orphan_chrome` should handle this)
- Memory per process (should be ~100-200MB per Chromium instance)

---

## 3. Database Connection Leaks

### Check SQLAlchemy connection pool
```bash
kubectl -n free-games-claimer exec free-games-claimer-XXXX-XXXX -- python3 -c "
from src.core.database import engine
print(f'Connection pool size: {engine.pool.size()}')
print(f'Checked out: {engine.pool.checkedout()}')
"
```

**Look for:**
- Connection count growing over time
- Connections not returned to pool

---

## 4. Scheduler Memory Growth (Long-running process)

### Monitor RSS over time
```bash
# Check RSS growth
kubectl -n free-games-claimer top pods --containers | grep free-games-claimer
```

**Look for:**
- Memory steadily increasing between runs (indicates a leak)
- Memory that doesn't drop after a run completes

---

## 5. Process Memory Breakdown (Quick Test)

### See exact memory usage by subprocess
```bash
kubectl -n free-games-claimer exec free-games-claimer-XXXX-XXXX -- python3 -c "
import psutil, os
proc = psutil.Process()
mem = proc.memory_info()
print(f'RSS: {mem.rss/1024/1024:.0f}MB')
for p in proc.children(recursive=True):
    try:
        pmem = p.memory_info()
        print(f'  {p.name()}: {pmem.rss/1024/1024:.0f}MB')
    except: pass
"
```

**This tells you exactly which subprocess is using memory.**

---

## Installation

To run these commands, you may need to install additional packages in the container:

```bash
pip install pympler memory_profiler psutil
```

---

## Expected Findings

Based on the codebase, **most likely culprits** for further memory gains:

1. **SQLAlchemy session objects** - Are sessions properly closed after database operations?
2. **Playwright contexts** - Are browser contexts fully cleaned up? (`_sweep_orphan_chrome` should handle this)
3. **Cached game data** - Does `aggregated_results` or similar grow unbounded?
4. **Store instances** - Are claimer objects kept alive unnecessarily?

---

## Notes

- Current memory: **142MB idle** (down from 175MB)
- Normal for Playwright + Python
- Further gains would require identifying specific leaks via profiling
- The 142MB is already quite lean for this type of application
