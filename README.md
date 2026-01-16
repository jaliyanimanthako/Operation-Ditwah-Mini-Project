# 🌪️ Operation Ditwah – Crisis Intelligence Pipeline
### AI Engineer Essentials | Mini Project 0

**Scenario:** Post-Cyclone Ditwah Relief (Sri Lanka), December 2025  
**Role:** AI Engineer for the Disaster Management Center (DMC)  
**Status:** 🚨 Active Development

---

## 📋 The Mission

Cyclone Ditwah has devastated Sri Lanka. The Disaster Management Center (DMC) is drowning in data. Your mission is to engineer a **Crisis Intelligence Pipeline** that is:

1.  **Reliable:** Distinguishes real SOS calls from news noise (Few-Shot Learning).
2.  **Safe:** Proves the system won’t “hallucinate” rescue boats (Temperature Control).
3.  **Strategic:** Plans complex logistics when resources are scarce (CoT & ToT).
4.  **Efficient:** Rejects spam to save API costs (Token Economics).
5.  **Scalable:** Processes a live news feed into an Excel database (Pydantic + Pandas).

---

## 🏗️ Project Structure & Requirements

### Part 1: The "Contract" & Few-Shot Learning (20 Points)
**Objective:** Classify incoming messages to distinguish legitimate SOS calls from general news.

*   **Input:** `data/Sample Messages.txt`
*   **Key Technique:** Few-Shot Prompting (Constraint: At least 4 labeled examples).
*   **Output Contract:** `District: [Name] | Intent: [Category] | Priority: [High/Low]`
*   **Deliverable:** `output/classified_messages.xlsx`
*   **Script:** `message_classification.py` (or `Part 1/message_classification.py`)

### Part 2: The Stability Experiment (Temperature Stress Test) (15 Points)
**Objective:** Evaluate system reliability and determinism under different model parameters.

*   **Input:** `data/Scenarios.txt`
*   **Experiment:**
    *   **Chaos Mode:** Run CoT prompt 3x with `temperature=1.0`.
    *   **Safe Mode:** Run CoT prompt 1x with `temperature=0.0`.
*   **Deliverable:** Console output comparison and commentary on hallucinations/drift.
*   **Script:** `cot_scenarios.py`

### Part 3: The Logistics Commander (CoT & ToT) (20 Points)
**Objective:** Optimize rescue operations with limited resources (1 boat at Ragama).

*   **Input:** `data/Incidents.csv` (contains 3 critical incidents).
*   **Step A (Scoring - CoT):** Assign Priority Score (1-10) based on Age, Need, and Urgency.
    *   *Logic:* Base 5 + Age(>60 or <5) + Life Threat + Medicine Need.
*   **Step B (Strategy - ToT):** Plan the optimal route.
    *   *Constraints:* Ragama → Ja-Ela (10m), Ja-Ela → Gampaha (40m).
    *   *Branches:*
        1.  Greedy (Highest Score First)
        2.  Speed (Closest First)
        3.  Logistics (Furthest First)
*   **Outcome:** Model selects the route leveraging maximum priority score saved per minute.
*   **Scripts:** `cot_scoring.py`, `logistic_commander.py`, `tot_stratergy.py`

### Part 4: The "Budget Keeper" (Token Economics) (15 Points)
**Objective:** Manage API costs by summarizing or truncating long/spam messages.

*   **Logic:**
    *   If message > 150 tokens → Truncate or Summarize (`overflow_summarize.v1`).
    *   Detect and Block Spam.
*   **Success Check:** Print "BLOCKED" or "TRUNCATED" for applicable inputs.
*   **Script:** `Budget_keeper.py`

### Part 5: The "News Feed" Extraction Pipeline (30 Points)
**Objective:** Convert raw text into a structured, validated database.

*   **Input:** `data/News Feed.txt`
*   **Output:** `output/flood_report.xlsx`
*   **Process:**
    1.  Extract JSON from text (`json_extract.v1`).
    2.  Validate using **Pydantic** schema `CrisisEvent`.
    3.  Save valid entries to Excel.
*   **Pydantic Schema:**
    *   `district` (Literal: 25 Districts)
    *   `flood_level_meters` (float/None)
    *   `vicLm_count` (int, default 0)
    *   `main_need` (str)
    *   `status` (Literal: Critical, Warning, Stable)
*   **Scripts:** `extract_json.py`, `Crisisevent.py`

---

## 🚀 Setup & Execution

1.  **Environment Setup:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Configuration:**
    Ensure your `.env` file contains valid API keys:
    ```env
    GOOGLE_API_KEY=...
    OPENAI_API_KEY=...
    ```

3.  **Running the Pipeline:**

    *   **Part 1:** `python miniproject/Part 1/message_classification.py`
    *   **Part 2:** `python miniproject/cot_scenarios.py`
    *   **Part 3:** `python miniproject/Part 3/logistic_commander.py`
    *   **Part 4:** `python miniproject/Budget_keeper.py`
    *   **Part 5:** `python miniproject/Part 5/Crisisevent.py`

---

## 📊 Grading Criteria (Total: 100 Points)

| Part | Component | Points |
|------|-----------|--------|
| 1 | Few-Shot Classification & Contract | 20 |
| 2 | Stability Stress Test | 15 |
| 3 | Logistics (CoT & ToT) | 20 |
| 4 | Token Economics | 15 |
| 5 | Extraction Pipeline & Validation | 30 |

---

## 🙏 Acknowledgments

> "Great engineering is about using the right tool for the job."

This project was developed as part of the **AI Engineer Essentials** curriculum at **Zuu Academy**.

*   **Course Module:** Week 01 – Prompt Engineering Essentials
*   **Assignment:** Mini Project 0 – Operation Ditwah
*   **Special Thanks:** To the Zuu Academy team for the scenario design and datasets.

---

**Author:** Jaliya  
**Course:** AI Engineer Essentials @ Zuu Academy
