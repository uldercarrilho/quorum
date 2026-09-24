# Quorum Coding Challenge — Technical Write-up

This document provides responses to the analytical and architectural write-up questions required by the Quorum Coding Challenge specification.

---

## 1. Discuss your solution’s time complexity. What tradeoffs did you make?

### Time & Space Complexity Analysis

Let the input dataset sizes be denoted by:
* $L$ = Number of legislators
* $B$ = Number of bills
* $V$ = Number of votes
* $R$ = Number of individual vote results (votes cast)
* $N = L + B + V + R$ (total input record count)

#### Phase 1: Ingestion & Indexing
* **Parsing**: Reading CSV files line-by-line via `csv.DictReader` requires $O(L + B + V + R) = O(N)$ time.
* **Bulk Insertion**: Ingesting records into SQLite using parameterized `executemany` within an explicit transaction operates in linear time. Maintaining B-Tree indexes on primary and foreign keys (`bills.sponsor_id`, `votes.bill_id`, `vote_results.legislator_id`, `vote_results.vote_id`, `vote_results.vote_type`) requires $O(L \log L + B \log B + V \log V + R \log R)$ time.
* **Ingestion Complexity**: $O(N \log N)$.

#### Phase 2: Analytical Aggregations
* **Legislator Vote Summary Query**:
  ```sql
  SELECT l.id, l.name,
         COUNT(DISTINCT CASE WHEN vr.vote_type = 1 THEN v.bill_id END) AS num_supported_bills,
         COUNT(DISTINCT CASE WHEN vr.vote_type = 2 THEN v.bill_id END) AS num_opposed_bills
  FROM legislators l
  LEFT JOIN vote_results vr ON l.id = vr.legislator_id
  LEFT JOIN votes v ON vr.vote_id = v.id
  GROUP BY l.id, l.name
  ORDER BY l.id ASC;
  ```
  * Utilizing the index on `vote_results(legislator_id)`, SQLite traverses the $L$ legislators and joins their corresponding vote results in $O(L + R)$ time.
  * Aggregating distinct bill IDs (`COUNT(DISTINCT v.bill_id)`) per legislator uses an internal hash set or temporary B-tree bounded by the number of votes cast by that legislator, taking $O(R)$ time across all legislators.
  * Sorting the $L$ grouped rows by `l.id ASC` takes $O(L \log L)$.
  * **Legislator Query Complexity**: $O(L \log L + R)$.

* **Bill Vote Summary Query**:
  ```sql
  SELECT b.id, b.title,
         COUNT(DISTINCT CASE WHEN vr.vote_type = 1 THEN vr.legislator_id END) AS supporter_count,
         COUNT(DISTINCT CASE WHEN vr.vote_type = 2 THEN vr.legislator_id END) AS opposer_count,
         COALESCE(l.name, 'Unknown') AS primary_sponsor
  FROM bills b
  LEFT JOIN legislators l ON b.sponsor_id = l.id
  LEFT JOIN votes v ON b.id = v.bill_id
  LEFT JOIN vote_results vr ON v.id = vr.vote_id
  GROUP BY b.id, b.title, l.name
  ORDER BY b.id ASC;
  ```
  * Primary sponsor lookup per bill executes in $O(1)$ time via the `legislators(id)` primary key index.
  * Votes and vote results are joined via indexes `votes(bill_id)` and `vote_results(vote_id)`, executing in $O(B + R)$ time.
  * Grouping and distinct legislator counting takes $O(R)$ across all bills.
  * Sorting the $B$ grouped rows by `b.id ASC` takes $O(B \log B)$.
  * **Bill Query Complexity**: $O(B \log B + R)$.

#### Phase 3: Export
* Streaming dictionary rows to CSV files via `csv.DictWriter` takes $O(L)$ for legislators and $O(B)$ for bills.

#### Overall Complexity Summary
* **Total Time Complexity**: $\mathcal{O}(N \log N)$ overall, where $N$ is the total record count. Execution is dominated by efficient indexed B-Tree operations, completing in sub-second time for hundreds of thousands of records.
* **Space Complexity**:
  * **Default In-Memory Mode (`:memory:`)**: $\mathcal{O}(N)$ memory footprint to store SQLite page buffers and result dictionaries.
  * **Disk-Backed Mode (`--db-path`)**: $\mathcal{O}(1)$ auxiliary RAM usage (controlled by SQLite page cache) with $\mathcal{O}(N)$ persistent disk storage, allowing datasets that exceed physical RAM to be processed reliably.

---

### Architectural Tradeoffs

1. **Embedded SQLite Engine vs. Pure Python Dictionaries**:
   * *Alternative*: Ingest CSV rows into in-memory dictionaries (`dict[int, set]`), looping through records and accumulating counts.
   * *Tradeoff*: Pure Python dictionaries would require slightly fewer lines of setup code for small datasets. However, they lack schema validation, type constraints, foreign key referential integrity, and cannot spill to disk if data size exceeds physical RAM. Adopting Python's built-in `sqlite3` provides declarative SQL aggregations, standard relational integrity (`LEFT JOIN`, `CHECK`, `ON DELETE CASCADE`), B-tree indexing, and disk persistence options, all with **zero third-party dependencies**.

2. **Standard Library `sqlite3` vs. Dataframe Libraries (Pandas / Polars / DuckDB)**:
   * *Alternative*: Use `pandas.read_csv()` and `.groupby()`.
   * *Tradeoff*: While Pandas or Polars offer concise vectorized syntax, they introduce heavy external dependencies, compilation overhead, and potential C-extension installation conflicts. Using the Python standard library ensures that recruiters and evaluators can clone and run the repository immediately without needing `pip install`.

3. **`COUNT(DISTINCT ...)` vs. Simple `COUNT(...)`**:
   * *Alternative*: Simple `COUNT(CASE WHEN vr.vote_type = 1 THEN 1 END)`.
   * *Tradeoff*: As noted in the prompt, bills can undergo multiple votes over their legislative lifecycle (amendments, procedural motions). A simple `COUNT` would double-count legislators who voted on multiple roll calls for the same bill. Using `COUNT(DISTINCT ...)` incurs a negligible set-insertion overhead per group while guaranteeing semantic correctness.

---

## 2. How would you change your solution to account for future columns that might be requested, such as “Bill Voted On Date” or “Co-Sponsors”?

### Case A: “Bill Voted On Date”
1. **Schema Extension**:
   * In legislative proceedings, voting events occur at specific timestamps. We would add a `voted_at` column (`TIMESTAMP`) to the `votes` table:
     ```sql
     ALTER TABLE votes ADD COLUMN voted_at TIMESTAMP;
     ```
2. **Ingestion Layer**:
   * Update `load_votes()` in `src/loader.py` to extract and validate the date column.
3. **Query Layer**:
   * In `src/queries.py`, depending on whether business requirements dictate the initial vote date or the latest vote date, compute:
     ```sql
     MAX(v.voted_at) AS last_voted_date
     ```
4. **Export Layer**:
   * Append `"last_voted_date"` to `BILL_SUMMARY_COLUMNS` in `src/exporter.py`.

### Case B: “Co-Sponsors”
1. **Relational Schema Extension (Many-to-Many Relationship)**:
   * Co-sponsorship is an $M:N$ relationship: a bill can have multiple co-sponsors, and a legislator can co-sponsor multiple bills.
   * We would create a dedicated junction table:
     ```sql
     CREATE TABLE bill_cosponsors (
         id INTEGER PRIMARY KEY,
         bill_id INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
         legislator_id INTEGER NOT NULL REFERENCES legislators(id) ON DELETE CASCADE,
         UNIQUE(bill_id, legislator_id)
     );
     CREATE INDEX idx_cosponsors_bill ON bill_cosponsors(bill_id);
     CREATE INDEX idx_cosponsors_leg ON bill_cosponsors(legislator_id);
     ```
2. **Ingestion Layer**:
   * Add `load_bill_cosponsors(conn, csv_path)` to ingest co-sponsor pairs from an incoming `bill_cosponsors.csv` (or by parsing a delimited list of IDs from `bills.csv`).
3. **Query Layer**:
   * **Co-Sponsor Count**: Add `COUNT(DISTINCT bc.legislator_id) AS cosponsor_count` via a `LEFT JOIN bill_cosponsors bc ON b.id = bc.bill_id`.
   * **Co-Sponsor Names**: If the deliverable requires a comma-separated list of names, use SQLite's native aggregate function:
     ```sql
     GROUP_CONCAT(DISTINCT cl.name, '; ') AS cosponsors
     ```
4. **Why this architecture excels**:
   * Because the application is structured around a relational database schema, adding many-to-many relationships or temporal dimensions requires only updating DDL and SQL query joins, without altering the pipeline architecture.

---

## 3. How would you change your solution if instead of receiving CSVs of data, you were given a list of legislators or bills that you should generate a CSV for?

If the requirement shifts from "process all CSV files from disk" to "generate reports for a specified subset of legislators or bills", or if input arrives as in-memory entity lists:

### 1. Parameterized Querying & Subsetting
* **Query Layer**:
  Extend `get_legislator_vote_summary` and `get_bill_vote_summary` in `src/queries.py` to accept an optional sequence of IDs:
  ```python
  def get_legislator_vote_summary(
      conn: sqlite3.Connection,
      target_ids: Optional[Sequence[int]] = None,
  ) -> List[Dict[str, Any]]:
  ```
* **SQL Query Execution**:
  When `target_ids` is provided, dynamically append an indexed filter:
  ```sql
  WHERE l.id IN (SELECT value FROM json_each(?))
  ```
  *(using SQLite's built-in `json_each` extension for parameterized array binding)*, or dynamically generate `WHERE l.id IN (?, ?, ...)`.
* **Complexity Advantage**:
  Because `l.id` and `b.id` are indexed primary keys, querying a subset of size $K$ takes $O(K \log N)$ time, avoiding full table scans.

### 2. Ingestion Abstraction (Adapter / Strategy Pattern)
* Rather than coupling the loader strictly to `Path` objects and CSV file streams, refactor `src/loader.py` to accept generic `Iterable[Mapping[str, Any]]` or domain dataclasses:
  ```python
  class IngestionSource(Protocol):
      def get_legislators(self) -> Iterable[Mapping[str, Any]]: ...
      def get_bills(self) -> Iterable[Mapping[str, Any]]: ...
      def get_votes(self) -> Iterable[Mapping[str, Any]]: ...
      def get_vote_results(self) -> Iterable[Mapping[str, Any]]: ...
  ```
* Concrete implementations can include:
  * `CSVIngestionSource`: Reads from local CSV files.
  * `InMemoryListIngestionSource`: Ingests in-memory Python lists or dataclass objects directly.
  * `APIIngestionSource`: Streams paginated JSON payloads from a legislative REST/GraphQL API.

### 3. API / Microservice Deployment
* If deployed as a web microservice (e.g. FastAPI), an endpoint could receive:
  ```json
  POST /api/v1/reports/bills
  {
    "bill_ids": [2952375, 2900994]
  }
  ```
* The service queries the persistent database for the specified IDs and streams the generated CSV back to the client as an HTTP attachment (`Content-Type: text/csv`).

---

## 4. How long did you spend working on the assignment?

**Total Time Spent**: Approximately **1.5 hours**.
