# Letras — Brazilian Gospel Lyrics Corpus

`letras` collects Brazilian Portuguese gospel song lyrics from an external
source, curates them down to a protestant/evangelical-only set, and publishes
the result as periodic dataset releases.

## Language

**Corpus**:
The curated collection of admitted gospel **Lyrics** that constitutes the product.
_Avoid_: dataset, database, dump (those describe a published snapshot, not the canonical set)

**Gospel**:
Portuguese-language **protestant/evangelical** Christian music; explicitly excludes Catholic devotional content and Afro-Brazilian/spiritist religious content.
_Avoid_: Christian, religious, worship (all too broad)

**Admission**:
The policy that decides whether a scraped **Lyric** qualifies for the **Corpus** — Portuguese language, 100–4000 characters, and not excluded by the Catholic / Afro-Brazilian / non-protestant keyword rules.
_Avoid_: filter, validation, cleaning

**Source**:
The external site (letras.mus.br) the corpus is scraped from. Its own "gospel" categorization is a starting point, not authoritative — **Admission** is.
_Avoid_: site, provider

**Artist**:
A performer listed under the **Source**'s gospel section, identified by a URL slug.
_Avoid_: band, singer

**Song**:
A track belonging to an **Artist**, identified by a slug.
_Avoid_: track, music

**Lyrics**:
The Portuguese text content of a **Song** — the unit that is admitted to (or rejected from) the **Corpus**.
_Avoid_: text, content

**Release**:
A periodic, dated published snapshot of the **Corpus** (the SQLite file plus derived exports).
_Avoid_: dump, backup, build

## Relationships

- An **Artist** has many **Songs**
- A **Song** has exactly one set of **Lyrics**
- **Lyrics** enter the **Corpus** only if they pass **Admission**
- **Gospel** scope is enforced by **Admission**, never assumed from the **Source**'s categorization
- A **Release** is a published snapshot of the **Corpus**

## Example dialogue

> **Dev:** "The **Source** lists this Padre's album under gospel — do we keep it?"
> **Domain expert:** "No. **Gospel** here means protestant/evangelical. **Admission** excludes Catholic artists and titles even when the **Source** files them under gospel."
>
> **Dev:** "So when someone downloads a **Release**, that's the whole **Corpus**?"
> **Domain expert:** "It's a snapshot of it on that date — the **Corpus** is the living curated set; a **Release** is what we froze and published."

## Flagged ambiguities

- **"gospel"** was ambiguous (could mean all Christian, or all religious music) — resolved: **Gospel** = Portuguese protestant/evangelical only; Catholic and Afro-Brazilian/spiritist content is excluded by **Admission**.
- **"dataset" / "dump" / "backup"** were used interchangeably for output — resolved: the canonical curated set is the **Corpus**; a published, dated snapshot is a **Release**.
- **"filter"** was used for corpus qualification — resolved: that policy is **Admission**. ("filter" is fine for incidental, non-domain uses.)
