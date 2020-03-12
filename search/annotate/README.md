
# Data

* Download data dictionary.
  * ftp://ftp.ncbi.nlm.nih.gov/dbgap/studies/phs000179/phs000179.v6.p2/pheno_variable_summaries/phs000179.v6.pht002239.v4.COPDGene_Subject_Phenotypes.data_dict.xml
* Download [MONDO json](http://purl.obolibrary.org/obo/mondo.json)

# Install:

pip install -r ../requirementst.txt

# Run:

python search/annotate/annotator.py ../dbGaP/phs000179.v6.pht002239.v4.COPDGene_Subject_Phenotypes.data_dict.xml 
