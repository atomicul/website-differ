# DESIGN.md: HTML Structural Diffing Engine (Logic & Implementation)

## 1. Overview
This document outlines the design and implementation logic for a "blind" HTML structural diffing engine. The tool takes two static `index.html` files and calculates a "Diff Score" ranging from `0.0` (identical layout) to `1.0` (complete rewrite). 

Because the engine cannot render the page or execute CSS/JavaScript, it relies strictly on two high-signal heuristics: the macroscopic arrangement of semantic landmarks, and a rich, four-dimensional fingerprint of the document's top-level wrappers.

## 2. Core Parsing Strategy
The implementation relies on an HTML parsing library to convert the raw HTML text into a navigable tree structure. Once the tree is built, the engine performs targeted extractions. All deep child nodes, inline text-formatting tags, and text content are explicitly ignored to filter out noise that does not impact the global visual layout.

## 3. Feature Extraction (The Two Heuristics)

The engine evaluates the document across two distinct dimensions. 

### A. Landmark Sequencing (40% of Global Score)
**Goal:** Detect if major sections of the page have been fundamentally reordered (e.g., a sidebar moving from the left to the bottom).

**Implementation:**
1. Walk through the entire document looking strictly for semantic landmark tags (`<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>`, `<section>`, `<article>`).
2. Ignore all nested structures and extract only the order in which these tags appear in the document flow.
3. Store this exact sequence as a list of strings representing the page's major block flow.



### B. Shallow Skeleton Fingerprinting (60% of Global Score)
**Goal:** Detect fundamental shifts in the page's foundational layout wrappers, styling hooks, and the volume of content shifting within them.

**Implementation:**
1. Locate the `<body>` tag to establish the root.
2. Traverse downward, strictly stopping after reaching a depth of two levels. 
3. For every structural element found within this shallow depth, generate a "Node Profile" containing exactly four specific data points:
   * **Tag Type:** The HTML element name (e.g., `div`, `main`, `section`).
   * **ID Attribute:** The unique identifier, if present (e.g., `app-root`).
   * **Class List:** The array of CSS classes applied to the element (e.g., `['container', 'flex', 'w-full']`).
   * **Child Node Count:** The absolute number of direct children nested inside this specific element.
4. Ignore any elements that do not act as structural containers (like plain text nodes).
5. Store the resulting sequence of these 4-datapoint Node Profiles. 



## 4. Calculating the Diff Score

Once the features are extracted from both the "Old" and "New" documents, the engine calculates the difference for each heuristic.

### Step 1: Evaluating the Landmark Sequence
To compare the landmark lists, the engine uses a sequence matching algorithm to find the longest contiguous matching sub-sequences. It returns a similarity ratio representing how much of the sequence remains intact. We subtract this ratio from `1.0` to get the **Landmark Difference Score**.

### Step 2: Evaluating the Shallow Skeleton Fingerprint
Comparing the skeleton profiles is a multi-layered process. First, the engine aligns the old sequence of nodes with the new sequence. Then, for each aligned pair of nodes, it calculates a **Node Difference Score** by evaluating the four data points with individual weights:

1. **Tag Type Match (e.g., 30% Node Weight):** The engine checks if the HTML tags are identical. A structural swap from a `<header>` to a `<div>` at the root level is a significant visual change. If they match, the difference is 0.0; if not, it is 1.0.
2. **Class List Volatility (e.g., 30% Node Weight):** The engine compares the two arrays of CSS classes using a set-similarity metric (like Jaccard similarity). It calculates the percentage of shared classes versus unique classes. This detects framework swaps or major styling changes on identical tags.
3. **ID Match (e.g., 20% Node Weight):** The engine compares the `id` strings. Because IDs dictate high-level targeted styling and JavaScript hooks, a changed or removed ID on a layout wrapper is heavily penalized.
4. **Child Count Volatility (e.g., 20% Node Weight):** The engine calculates the absolute difference between the old child count and the new child count, relative to the maximum of the two. This detects "Layout Rebalancing." For example, if an element goes from having 50 children to 2 children, a massive visual shift has occurred within that container, even if the tag, ID, and classes are identical.

The engine calculates the average Node Difference Score across all aligned nodes in the skeleton to produce the final **Skeleton Difference Score**.

### Step 3: Final Composite Score
The engine calculates the final composite Diff Score by applying the global weights:
* `(Landmark Difference Score * 0.40) + (Skeleton Difference Score * 0.60)`

## 5. Threshold Interpretation
The final score is interpreted to trigger appropriate alerts:
* **Score > 0.40:** Massive structural rewrite or major layout shift detected. The topmost structural nodes, their styling hooks, or their respective contents have fundamentally changed.
* **Score > 0.15:** Significant layout modifications detected. Major semantic blocks have been reordered, or wrappers have grown/shrunk significantly.
* **Score < 0.15:** Minor structural changes. This is likely routine content churn that does not impact the global visual geometry.

## 6. Implementation details

Use python with BeautifulSoup. The script should be contained in a single file. Format and lint with ruff. Use type hints. Static checks with pyright.
