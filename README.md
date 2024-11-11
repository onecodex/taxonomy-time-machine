# taxonomy-time-machine

## Data Structure

### Compressed Taxonomy Table

### Change Log

1. Easier to see what's happening
2. Ability to capture events like `DELETED`, `MERGED`, and `RENAMED`
3. More difficult to create (need to compare previous event)
4. Must be created _ab initio_ each time

```
event_name,version,tax_id,name,rank,parent_id,merged_tax_id
CREATED,1,9606,homo sapiens,species,9605
RENAMED,2,9606,homo sapiens2,species,9607
MERGED,...
DELETED,...
```
