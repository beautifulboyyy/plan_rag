## Input

**Original Question (Q) - Trust Source:**
{question}

**Memory (M) - Trust Source (if available):**
{memory}

**Plan to Verify (Verify Target) - May contain hallucinations:**
{plan}

## Trust Protocol: Extract Only

### From Q or M (TRUSTED): Extract Anchor Entity
- The who/what to search for
- Example: "the director of film Polish-Russian War", "John V Prince of Anhalt-Zerbst"

### From Plan (UNTRUSTED): Extract Target Relation ONLY
- Find the relationship phrase (verb + preposition)
- **DO NOT extract any names, values, or objects from Plan**
- Extract: "mother of", "died in", "born on", "director of"
- Discard: names, dates, awards, etc.

### Common Relation Patterns
| Question Pattern | Relation to Extract | Example |
|-----------------|---------------------|---------|
| "Who is X?" | "Who is" | X's mother |
| "When did X die?" | "When did" | X died in 1516 → "When did X" |
| "Where was X born?" | "Where was" | X born in Berlin → "Where was X" |
| "What award did X win?" | "What award did" | X won Award Y → "What award did X" |

## Output Format

Anchor Entity: [from Q or M only - who/what to search for]
Target Relation: [from Plan only - verb phrase, NO objects/names]
Query: [natural query: relation + anchor entity]

## Examples

**Example 1: "Who is X?" question**

Q: "Who is the mother of the director of Polish-Russian War?"
Plan: "The director is Aleksander Ford."  ← WRONG name, DISCARD

Anchor Entity: the director of Polish-Russian War
Target Relation: Who is
Query: Who is the director of Polish-Russian War's mother

**Example 2: "When did X die?" question**

Q: "When did John V, Prince of Anhalt-Zerbst's father die?"
Plan: "John's father was Ernest I, Prince of Anhalt-Dessau who died in 1516."  ← 1516 may be WRONG

Anchor Entity: John V Prince of Anhalt-Zerbst's father
Target Relation: When did ... die
Query: When did John V Prince of Anhalt-Zerbst's father die

**Example 3: With Memory (use verified entity from M)**

Q: "Who is the mother of X?"
Memory: "X is the director of Polish-Russian War"  ← VERIFIED
Plan: "X's mother is Y."  ← WRONG name

Anchor Entity: X, director of Polish-Russian War (from Memory)
Target Relation: Who is
Query: Who is X, director of Polish-Russian War's mother

## Important Rules
1. Anchor Entity ALWAYS comes from Q or M (never from Plan)
2. Target Relation comes from Plan, but ONLY the verb phrase
3. Never use Plan's names/dates/values in the Query
4. If Memory has verified entity, use that for Anchor
