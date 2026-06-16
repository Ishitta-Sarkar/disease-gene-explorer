import csv


class DiseaseGeneExplorer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.records = self.load_data()

    def load_data(self):
        records = []

        with open(self.file_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                records.append(row)

        return records

    def get_all_diseases(self):
        diseases = sorted(set(record["disease"] for record in self.records))
        return diseases

    def get_genes_by_disease(self, disease_name):
        disease_name = disease_name.lower()

        return [
            record for record in self.records
            if record["disease"].lower() == disease_name
        ]

    def search_gene(self, gene_name):
        gene_name = gene_name.upper()

        return [
            record for record in self.records
            if record["gene"].upper() == gene_name
        ]

    def summarize_disease(self, disease_name):
        genes = self.get_genes_by_disease(disease_name)

        if not genes:
            return f"No records found for {disease_name}."

        summary = f"Disease: {disease_name.title()}\n"
        summary += f"Number of associated genes: {len(genes)}\n\n"

        for record in genes:
            summary += f"Gene: {record['gene']}\n"
            summary += f"Biological Role: {record['biological_role']}\n"
            summary += f"Relevance: {record['relevance']}\n\n"

        return summary.strip()
