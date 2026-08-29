# Demonstration guide

This walkthrough explains the project in the same order that data moves through it. It uses synthetic data only.

## 1. Open the project

Open the repository root in VS Code. The most useful files to keep visible are:

- `data/input/resume_01_data_engineer.md` — unstructured source input.
- `examples/ingested_resume.json` — blueprint-aligned ingestion output.
- `config/resume_blueprint.json` — human-readable blueprint.
- `config/resume.schema.json` — machine-enforced JSON contract.
- `config/neo4j_schema.json` — allowed graph labels and relationships.
- `src/document_ingest.py` — structure-preserving PDF stage.
- `src/qwen_parser.py` — optional local model extraction.

## 2. Explain the two ingestion stages

### Document structure

The first stage reads the PDF as a document. It keeps:

- Pages and sections.
- Ordered text blocks.
- Tables and their rows.
- Embedded images.
- Hyperlinks.
- Bounding boxes.
- Captions and nearby context.
- File hashes and parser metadata.

Run it with:

```powershell
.\.venv\Scripts\python.exe -m src.document_ingest --input data\pdf_samples --output data\structured --assets data\structured_assets
.\.venv\Scripts\python.exe -m src.validate_documents --input data\structured --schema config\document.schema.json
```

Open `data/structured/synthetic_resume.document.json` and show `document`, `hierarchy`, `blocks`, and `assets` separately.

### Resume entities

The second stage maps resume content into the domain blueprint:

- Global candidate fields: name, contact details, headline, and summary.
- Section entities: skills, experience, education, projects, certifications, and languages.
- Source metadata: filename, hash, ingestion time, and parser version.

Run the deterministic synthetic demonstration:

```powershell
.\.venv\Scripts\python.exe -m src.ingest --input data\input --output data\processed --parser deterministic
.\.venv\Scripts\python.exe -m src.validate --input data\processed --expected 10
```

Open `data/processed/resume_01_data_engineer.json`. Point out that the candidate name is preserved as written and that `candidate_id` is not part of the public ingestion output.

## 3. Explain schema validation

The blueprint describes what the system intends to extract. JSON Schema enforces that intention.

For example:

- `candidate.name` must be non-empty.
- Every skill must have `name` and `category`.
- Experience records must contain their defined fields.
- Unknown top-level properties are rejected.
- A source SHA-256 value must have the expected format.

The command

```powershell
.\.venv\Scripts\python.exe -m src.validate --input data\processed --expected 10
```

checks structure and types. It does not prove that every value came from the original PDF.

## 4. Explain provenance

Provenance performs the second kind of validation. It attempts to match each extracted value back to a source block and records:

- Page number.
- Section identifier.
- Block identifier.
- Bounding box.
- Source quotation.
- Match type and score.

For the Qwen PDF path:

```powershell
.\.venv\Scripts\python.exe -m src.ingest --input data\pdf_samples\synthetic_resume.pdf --output data\processed_pdf --parser qwen --model qwen2.5:7b
.\.venv\Scripts\python.exe -m src.provenance --resumes data\processed_pdf --documents data\structured --output data\provenance
```

An ungrounded claim stays visible for review. It is not silently presented as verified source truth.

## 5. Build the graph

Build and validate the synthetic domain graph:

```powershell
.\.venv\Scripts\python.exe -m src.build_graph_json --input data\processed --output data\graph.json
```

The command produces 179 nodes and 208 relationships from the ten synthetic resumes.

For a clean Neo4j presentation, create the compact CSV export:

```powershell
.\.venv\Scripts\python.exe -m src.export_demo_graph --input data\processed --output data\neo4j_demo_import
docker compose up -d
Get-Content config\neo4j_demo_import.cypher | docker compose exec -T neo4j cypher-shell -u neo4j -p resume-password
```

This presentation layer deliberately excludes page-layout and provenance properties. The full graph still supports those elements; the demo view is optimized for explanation.

## 6. Neo4j queries

### Entire candidate-centred graph

```cypher
MATCH p=(candidate:Candidate)-[*1..2]-(entity)
RETURN p
LIMIT 300;
```

### Candidates and skills

```cypher
MATCH (candidate:Candidate)-[:HAS_SKILL]->(skill:Skill)
RETURN candidate.name, collect(skill.name) AS skills
ORDER BY candidate.name;
```

### Work history

```cypher
MATCH (candidate:Candidate)-[:HAS_EXPERIENCE]->(experience:Experience)-[:AT_COMPANY]->(company:Company)
RETURN candidate.name, experience.job_title, company.name, experience.start_date, experience.end_date;
```

### Projects and technologies

```cypher
MATCH (candidate:Candidate)-[:WORKED_ON]->(project:Project)
OPTIONAL MATCH (project)-[:USES]->(technology:Technology)
RETURN candidate.name, project.name, collect(technology.name) AS technologies;
```

## 7. Explain the graph model

- A node represents an entity, such as a candidate, skill, company, or project.
- A relationship states how two entities are connected.
- Shared entities are merged. Two candidates who list Python connect to the same `Skill` node.
- Relationship properties hold contextual information when it belongs to the connection rather than either entity.
- `neo4j_schema.json` defines which label-to-label directions are legal.

## 8. Demonstrate Chroma

Load normalized resume sections:

```powershell
.\.venv\Scripts\python.exe -m src.chroma_store load --input data\processed --reset
.\.venv\Scripts\python.exe -m src.chroma_store query "streaming data pipelines" --top-k 5
```

Load layout-aware PDF blocks:

```powershell
.\.venv\Scripts\python.exe -m src.structured_chroma load --input data\structured --reset
.\.venv\Scripts\python.exe -m src.structured_chroma query "profile illustration" --top-k 5
```

Neo4j answers explicit relationship questions. Chroma answers similarity questions. They complement one another.

## 9. Explain image processing

The synthetic profile illustration demonstrates the complete path:

- The image bytes are extracted to `data/structured_assets`.
- The document JSON records its hash, dimensions, MIME type, page, and bounding box.
- Nearby text blocks provide context.
- Neo4j connects the image to the document hierarchy and contextual blocks.
- Chroma embeds the textual context and keeps the image path as metadata.

The binary image itself is not misrepresented as text.

## 10. Finish with verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected result:

```text
11 passed
```

The final point to emphasize is that reliability begins with the knowledge representation: structure, provenance, validation, and privacy are established before retrieval or downstream model reasoning.
