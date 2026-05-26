# CLI Tool Architecture

The following diagram illustrates the architecture of the CLI tool, detailing the flow of data through Parsing, Annotation, Crawling (Concept Expansion), and Indexing.

## Data Models
- **DugElement**: Base class for searchable items.
  - **DugVariable**: Represents a variable (e.g., from DbGaP).
  - **DugStudy**: Represents a study.
  - **DugSection**: Represents a section/CRF.
  - **DugConcept**: Represents a standardized concept (e.g., a disease or gene term).
- **DugIdentifier**: Represents a raw identifier returned by an external annotator (e.g., Monarch, Sapbert).

## Architecture Diagram

```mermaid
graph TD
    subgraph "CLI Entry Point"
        CLI["cli.py: crawl()"]
    end

    subgraph "Data Loading & Parsing"
        InputFile[Input File]
        Parser["Parser<br/>(e.g., DbGaPParser)"]
        InputFile -->|Raw Data| Parser
        Parser -->|Produces List| Elements["List<DugElement><br/>(DugVariable, DugStudy, DugSection)"]
    end

    subgraph "Annotation Phase"
        Elements -->|ml_ready_desc| Annotator["Annotator<br/>(Monarch, Sapbert)"]
        Annotator -->|External API Call| API["External API<br/>(Biolink, etc.)"]
        API -->|Response| Annotator
        Annotator -->|Returns| Identifiers[List<DugIdentifier>]
        Identifiers -->|Converted to| Concept[DugConcept]
        Concept -.->|Linked to| Elements
    end

    subgraph "Crawling & Concept Expansion"
        Concept -->|Input| Crawler[Crawler.expand_concept]
        Crawler -->|Queries| TranQL[TranQL Query Factory]
        TranQL -->|Executes Query| KG[Knowledge Graph]
        KG -->|Returns| KGAnswer[KG Answer]
        KGAnswer -->|Enriches| Concept
    end

    subgraph "Indexing Phase"
        Elements -->|Indexing| VarIndex[(Variables Index)]
        Elements -->|Indexing| StudyIndex[(Studies Index)]
        Elements -->|Indexing| SecIndex[(Sections Index)]
        
        Concept -->|Indexing| ConceptIndex[(Concepts Index)]
        Concept -->|Expanded KG| KGAnswerIndex[(KG Answer Index)]
    end

    CLI --> Parser
    CLI --> Annotator
    CLI --> Crawler
    
    style InputFile fill:#f9f,stroke:#333,stroke-width:2px
    style CLI fill:#ccf,stroke:#333,stroke-width:2px
    style Parser fill:#ff9,stroke:#333,stroke-width:2px
    style Annotator fill:#ff9,stroke:#333,stroke-width:2px
    style Crawler fill:#ff9,stroke:#333,stroke-width:2px
    style TranQL fill:#ff9,stroke:#333,stroke-width:2px
```

## Detailed Data Flow

1.  **Parsing**: The `Parser` reads the input file (xml, csv, etc.) and instantiates `DugElement` objects (specifically `DugVariable`, `DugStudy`, or `DugSection`).
2.  **Annotation**: The `Annotator` takes the `ml_ready_desc` (description text) from each `DugElement` and queries an external service (like Monarch). It returns `DugIdentifier` objects. These `DugIdentifier` objects are used to create `DugConcept` objects, which are then linked to the original `DugElement`.
3.  **Crawling (Concept Expansion)**: The `Crawler` iterates through the unique `DugConcept` objects. It uses `TranQL` to execute queries against a broader Knowledge Graph (KG) to find related concepts and "answers". These answers are stored within the `DugConcept`.
4.  **Indexing**:
    -   `DugElement` objects are indexed into their respective Elasticsearch indices (`variables_index`, `studies_index`, `sections_index`).
    -   `DugConcept` objects are indexed into the `concepts_index`.
    -   The Knowledge Graph answers found during expansion are indexed into the `kg_index`.
