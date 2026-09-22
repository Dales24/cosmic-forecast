# Classifier holdouts

For real-image experiments, supply a CSV manifest with columns
`path,label,group,split`. Paths resolve relative to the manifest directory and
must stay within it. Labels use the repository class slugs. Split names are
`train`, `validation`, and `test`, and all three must be nonempty.

```csv
path,label,group,split
images/sat-a.png,satellite,object-a-session-1,train
images/sat-b.png,satellite,object-b-session-2,validation
images/sat-c.png,satellite,object-c-session-3,test
```

Assign related observations to the same group before training. If objects or
sessions overlap, put the whole connected set in one group; concatenating IDs
alone does not prevent an object appearing in several groups. The loader checks
group disjointness, repeated paths and identical resized RGB pixels across
partitions. It cannot detect incorrect group assignments or near-duplicates.
Every held-out label must occur in training; the report lists class counts,
including absent classes, rather than implying coverage of the whole registry.

```powershell
uv run python -m scripts.train_object_classifier --manifest data/images/manifest.csv --prepare-only
uv run python -m scripts.train_object_classifier --manifest data/images/manifest.csv --output models/classifier_run_001 --epochs 10
```

Preparation validates data and prints counts without creating a model. Manifest
paths resolve from the repository root when relative; individual image paths
resolve from the manifest directory. Choose a new output directory for each run.
Manifest runs reject resuming an existing model because its training provenance
cannot establish independence from the test partition.

Training sees only train/validation data. After normal completion, the CLI
evaluates the test partition and saves `evaluation.json` with loss/accuracy,
manifest and model-input hashes, class/group counts and completion status.
Interrupted runs save partial weights and status without test metrics. The
evaluation report accompanies the primary output, not archived copies.
Avoid using repeated test-set results to tune models; reserve a new final test
set if this happens. This software does not establish dataset representativeness,
label correctness or scientific validity. Images currently load into memory.

Legacy `--data-dir` still uses a random image split and provides no independent
test set. Use the manifest workflow for controlled holdouts.
