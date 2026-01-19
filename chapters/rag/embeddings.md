## Embeddings

Embeddings are the mechanism that transforms raw data (text, images, audio, etc.) into numerical vectors such that semantic similarity becomes geometric proximity.

### Historical perspective

The idea of representing language as vectors predates modern deep learning. Early information retrieval systems in the 1960s and 1970s relied on sparse vector representations such as term-frequency and TF-IDF, motivated by the *distributional hypothesis*: words that appear in similar contexts tend to have similar meanings. These approaches treated language as a high-dimensional but mostly empty space, where each dimension corresponded to a vocabulary term.

In the early 2010s, research shifted toward *dense* representations that could be learned from data. Neural language models demonstrated that low-dimensional continuous vectors could encode syntactic and semantic regularities far more effectively than sparse counts. This transition laid the foundation for modern embedding-based retrieval systems and, eventually, for Retrieval-Augmented Generation.

### From word counts to vector spaces (intuition)

A simple way to build intuition is to start with word-count vectors. Consider the sentence:

> “The cat is under the table”

If the vocabulary is `{the, cat, is, under, table}`, the sentence can be represented as a vector of counts:

```
[the: 2, cat: 1, is: 1, under: 1, table: 1]
```

This representation is easy to construct and works reasonably well for keyword matching. However, it has two fundamental limitations. First, it is *sparse* and high-dimensional, which makes storage and comparison inefficient. Second, it carries no notion of meaning: “cat” and “dog” are as unrelated as “cat” and “table” unless they literally co-occur.

Modern embeddings keep the core idea—mapping language to vectors—but replace sparse counts with dense, learned representations where proximity reflects semantics rather than surface form.

![Image](img/word_embedding_space.png)

![Image](img/semantic_relevance.png)

### Dense semantic embeddings

Dense embeddings map words, sentences, or documents into a continuous vector space (often hundreds or thousands of dimensions). In this space, semantic relationships emerge naturally: synonyms cluster together, analogies correspond to vector offsets, and related concepts occupy nearby regions.

Early influential methods include **Word2Vec**, which learns word vectors by predicting context words, **GloVe**, which combines local context with global co-occurrence statistics, and **FastText**, which incorporates character n-grams to better handle morphology and rare words. These models marked a decisive shift from symbolic counts to geometric meaning.

Conceptually, these embeddings still rely on co-occurrence statistics, but they compress them into a dense space where distance metrics such as cosine similarity become meaningful signals for retrieval.

### Transformer-based embeddings

The next major step came with transformer architectures. Models such as **BERT** introduced *contextual embeddings*: a word’s vector depends on its surrounding words, so “bank” in “river bank” differs from “bank” in “investment bank”. This resolved a long-standing limitation of earlier static embeddings.

Transformer-based embedding models typically operate at the sentence or document level for retrieval. They encode an entire passage into a single vector that captures its overall meaning. In a RAG system, these vectors are indexed in a vector database and compared against query embeddings to retrieve semantically relevant context, even when there is little lexical overlap.

A minimal illustrative snippet for text embedding might look like:

```python
# Pseudocode: embed text into a dense vector
text = "The cat is under the table"
vector = embed(text)   # returns a dense float array
```

The key point is not the API, but the abstraction: text is projected into a semantic space where similarity search is efficient and meaningful.

### Multimodal generalization

The embedding concept generalizes naturally beyond text. Multimodal models learn a *shared* vector space for different data types, allowing cross-modal retrieval. A canonical example is **CLIP**, which aligns images and text descriptions so that an image of a “red chair” is close to the text “a red chair” in the same embedding space.

This generalization is increasingly important in modern RAG systems, where documents may include text, diagrams, tables, or images. A single embedding space enables unified retrieval across modalities, simplifying system design while expanding capability.

### Embeddings in the RAG pipeline

Within a RAG architecture, embeddings serve as the semantic interface between raw data and retrieval. During ingestion, documents are converted into vectors and indexed. At query time, the user question is embedded into the same space, and nearest-neighbor search retrieves the most relevant chunks. The quality of the embeddings directly determines recall, precision, and ultimately the factual grounding of the generated answers.

### References

1. Salton, G., Wong, A., & Yang, C. S. *A Vector Space Model for Automatic Indexing*. Communications of the ACM, 1975.
2. Mikolov, T., Chen, K., Corrado, G., & Dean, J. *Efficient Estimation of Word Representations in Vector Space*. arXiv, 2013.
3. Pennington, J., Socher, R., & Manning, C. *GloVe: Global Vectors for Word Representation*. EMNLP, 2014.
4. Bojanowski, P., Grave, E., Joulin, A., & Mikolov, T. *Enriching Word Vectors with Subword Information*. TACL, 2017.
5. Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. *BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding*. NAACL, 2019.
6. Radford, A. et al. *Learning Transferable Visual Models From Natural Language Supervision*. ICML, 2021.
