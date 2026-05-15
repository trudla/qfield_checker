This is a reposity for a VUK middleware that checks tree QField data and uploads them to a database.
Install using poetry install


## What it does
1. Connect to QField Cloud
2. Download the configured project
3. Find the configured GeoPackage files
4. Open each GeoPackage
5. Check whether `ready_for_upload.ready = 1`
6. If not set, skip the file
7. If set, load the `_L` and `_S` layers
8. Run checks
9. Write `error_flag` and `error_description`
10. Optionally reset the ready flag and upload the project back

## Assumption in this starter

This starter assumes the GeoPackage contains a layer/table named `ready_for_upload`
and that this layer has a column named `ready`.

If any row in that layer has `ready = 1`, the checks run.
If no row has `ready = 1`, the script exits.

When you run with `--upload`, the script resets `ready` back to `0` before uploading.
