# taxonomy-time-machine

## TODO:

- [x] Data Structure
- [ ] Queries
    - [ ] Fetch current lineage
    - [ ] Fetch current children/descendants
    - [ ] Fetch node history
- [ ] API
- [ ] Front End

## Data Structure

### Change Log

```
event_name,version,tax_id,parent_id,rank,name
create,dumps/taxdmp_2014-08-01,1418784,687330,genus,Cotaena
create,dumps/taxdmp_2014-08-01,1418785,1418784,species,Cotaena plenella
create,dumps/taxdmp_2014-08-01,418784,5475,species,Candida pseudohaemulonii
alter,dumps/taxdmp_2014-09-01,418784,1540022,species,Candida pseudohaemulonii
alter,dumps/taxdmp_2016-09-01,418784,1540022,species,[Candida] pseudohaemulonii
alter,dumps/taxdmp_2018-04-01,418784,1540022,species,[Candida] pseudohaemulonis
create,dumps/taxdmp_2018-11-01,2418784,1333472,species,Tanypodinae sp. BIOUG25744-B06
alter,dumps/taxdmp_2021-04-01,418784,1540022,species,[Candida] pseudohaemulonii
alter,dumps/taxdmp_2022-03-01,418784,36910,species,[Candida] pseudohaemulonii
alter,dumps/taxdmp_2022-05-01,418784,2937349,species,[Candida] pseudohaemulonii
alter,dumps/taxdmp_2022-08-01,418784,2964429,species,[Candida] pseudohaemulonii
alter,dumps/taxdmp_2024-06-01,418784,2964429,species,[Candida] pseudohaemuli
alter,dumps/taxdmp_2024-09-01,418784,3303203,species,Candidozyma pseudohaemuli
```
