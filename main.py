from src.disease_gene_tools import DiseaseGeneExplorer


explorer = DiseaseGeneExplorer("data/disease_genes.csv")

print("Disease Gene Explorer")
print("=" * 30)

print("\nAvailable Diseases:")
for disease in explorer.get_all_diseases():
    print("-", disease)

print("\nDiabetes Gene Summary")
print("-" * 30)
print(explorer.summarize_disease("diabetes"))

print("\nGene Search: APOE")
print("-" * 30)
results = explorer.search_gene("APOE")

for record in results:
    print("Disease:", record["disease"])
    print("Gene:", record["gene"])
    print("Biological Role:", record["biological_role"])
    print("Relevance:", record["relevance"])
