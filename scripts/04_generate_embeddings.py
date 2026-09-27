from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from tqdm import tqdm

from _database import create_db_engine


MODEL_NAME = "NeuML/bioclinical-modernbert-base-embeddings"
MODEL_BATCH_SIZE = 32
DATABASE_CHUNK_SIZE = 256


def build_clinical_text(row) -> str:
    components = []
    if row["admission_type"]:
        components.append(f"Admission: {row['admission_type']}")
    if row["drug"]:
        components.append(f"Prescribed: {row['drug']}")
    if row["test_name"]:
        components.append(f"Lab Test: {row['test_name']}")
    if row["drg_severity"]:
        components.append(f"Severity Level: {row['drg_severity']}")
    if row["description"]:
        components.append(f"Diagnosis: {row['description']}")
    if row["comments"]:
        components.append(f"Notes: {row['comments'][:250]}")
    return " | ".join(components)


def generate_and_store_embeddings() -> None:
    engine = create_db_engine()
    print("Loading local BioClinical ModernBERT model...")
    model = SentenceTransformer(MODEL_NAME, local_files_only=True)

    if model.get_sentence_embedding_dimension() != 768:
        raise ValueError(
            "Model output dimension does not match the database vector(768)."
        )

    with engine.connect() as conn:
        remaining = conn.execute(
            text(
                "SELECT COUNT(*) FROM patient_encounters "
                "WHERE clinical_embedding IS NULL"
            )
        ).scalar_one()

    if remaining == 0:
        print("All patient records already have embeddings.")
        return

    select_query = text(
        """
        SELECT id, admission_type, drug, test_name, drg_severity,
               description, comments
        FROM patient_encounters
        WHERE clinical_embedding IS NULL
        ORDER BY id
        LIMIT :chunk_size
        """
    )
    update_query = text(
        """
        UPDATE patient_encounters
        SET clinical_embedding = CAST(:embedding AS vector(768))
        WHERE id = :id
        """
    )

    print(f"Generating embeddings for {remaining:,} remaining records...")
    with tqdm(total=remaining, desc="Vectorizing records", unit="rows") as progress:
        while True:
            with engine.connect() as conn:
                batch = conn.execute(
                    select_query,
                    {"chunk_size": DATABASE_CHUNK_SIZE},
                ).mappings().all()

            if not batch:
                break

            clinical_texts = [build_clinical_text(row) for row in batch]
            embeddings = model.encode(
                clinical_texts,
                batch_size=MODEL_BATCH_SIZE,
                show_progress_bar=False,
            ).tolist()
            update_params = [
                {"id": row["id"], "embedding": str(embedding)}
                for row, embedding in zip(batch, embeddings)
            ]

            with engine.begin() as conn:
                conn.execute(update_query, update_params)

            progress.update(len(batch))

    print("All clinical records are vectorized and ready for hybrid search.")


if __name__ == "__main__":
    generate_and_store_embeddings()
