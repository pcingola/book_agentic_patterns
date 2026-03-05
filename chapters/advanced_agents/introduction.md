## Introduction

The previous chapters introduced the building blocks of agentic systems: tool use, memory, planning, orchestration, retrieval, and evaluation. This chapter composes those blocks into complete agent architectures that solve problems too complex or too sensitive for a single-pass prompt.

Each section presents a self-contained agent pattern with its design rationale, core data model, and a working implementation. The accompanying notebooks let you run each agent end-to-end and inspect intermediate state at every step.

The patterns covered are adversarial debate (structured opposition to pressure-test decisions), deep research (iterative evidence accumulation with gap detection), rubric-based evaluation (criteria-driven assessment with provenance), code indexing and search (structure-aware retrieval over repositories), and anonymization (layered de-identification with verification).
