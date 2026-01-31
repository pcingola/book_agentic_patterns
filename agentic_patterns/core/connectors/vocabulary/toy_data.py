"""Toy vocabularies for Phase 1 testing and development."""

from agentic_patterns.core.connectors.vocabulary.models import VocabularyTerm


def get_toy_enum_terms() -> list[VocabularyTerm]:
    """~10 terms mimicking Ensembl Biotypes (flat, no hierarchy)."""
    return [
        VocabularyTerm(id="protein_coding", label="Protein coding", synonyms=["mRNA"], definition="Gene/transcript that codes for a protein."),
        VocabularyTerm(id="lncRNA", label="Long non-coding RNA", synonyms=["lincRNA"], definition="Non-coding transcript longer than 200 nucleotides."),
        VocabularyTerm(id="miRNA", label="MicroRNA", synonyms=["micro RNA"], definition="Small non-coding RNA involved in post-transcriptional regulation."),
        VocabularyTerm(id="snRNA", label="Small nuclear RNA", definition="RNA found in the nucleus involved in splicing."),
        VocabularyTerm(id="snoRNA", label="Small nucleolar RNA", definition="RNA involved in chemical modifications of rRNAs and snRNAs."),
        VocabularyTerm(id="rRNA", label="Ribosomal RNA", definition="Structural component of ribosomes."),
        VocabularyTerm(id="tRNA", label="Transfer RNA", definition="Adaptor molecule that links codons to amino acids."),
        VocabularyTerm(id="pseudogene", label="Pseudogene", definition="Non-functional remnant of a gene."),
        VocabularyTerm(id="IG_gene", label="Immunoglobulin gene", synonyms=["Ig gene"], definition="Gene encoding immunoglobulin chains."),
        VocabularyTerm(id="TR_gene", label="T-cell receptor gene", synonyms=["TCR gene"], definition="Gene encoding T-cell receptor chains."),
    ]


def get_toy_tree_terms() -> list[VocabularyTerm]:
    """~20 terms mimicking a subset of Sequence Ontology (hierarchical)."""
    return [
        # Root
        VocabularyTerm(id="SO:0000110", label="sequence_feature", children=["SO:0000001", "SO:0000704"]),
        # Level 1
        VocabularyTerm(id="SO:0000001", label="region", parents=["SO:0000110"], children=["SO:0000316", "SO:0000204", "SO:0000139"]),
        VocabularyTerm(id="SO:0000704", label="gene", parents=["SO:0000110"], children=["SO:0001217", "SO:0000336"], definition="A region of biological sequence that encodes a gene."),
        # Level 2 - regions
        VocabularyTerm(id="SO:0000316", label="CDS", parents=["SO:0000001"], synonyms=["coding sequence"], definition="Contiguous sequence that codes for protein.", relationships={"part_of": ["SO:0000234"]}),
        VocabularyTerm(id="SO:0000204", label="five_prime_UTR", parents=["SO:0000001"], synonyms=["5' UTR"], relationships={"part_of": ["SO:0000234"]}),
        VocabularyTerm(id="SO:0000139", label="three_prime_UTR", parents=["SO:0000001"], synonyms=["3' UTR"], relationships={"part_of": ["SO:0000234"]}),
        # Level 2 - genes
        VocabularyTerm(id="SO:0001217", label="protein_coding_gene", parents=["SO:0000704"], synonyms=["protein gene"], definition="A gene that codes for a protein."),
        VocabularyTerm(id="SO:0000336", label="pseudogene", parents=["SO:0000704"], definition="A non-functional copy of a gene."),
        # Transcript
        VocabularyTerm(id="SO:0000234", label="mRNA", parents=["SO:0000673"], synonyms=["messenger RNA"], definition="Messenger RNA transcript."),
        VocabularyTerm(id="SO:0000673", label="transcript", parents=["SO:0000110"], children=["SO:0000234", "SO:0000655"], definition="An RNA synthesized from a DNA template."),
        VocabularyTerm(id="SO:0000655", label="ncRNA", parents=["SO:0000673"], synonyms=["non-coding RNA"], children=["SO:0000276", "SO:0000274"]),
        # ncRNA subtypes
        VocabularyTerm(id="SO:0000276", label="miRNA", parents=["SO:0000655"], definition="Micro RNA, ~22nt regulatory RNA."),
        VocabularyTerm(id="SO:0000274", label="snRNA", parents=["SO:0000655"], definition="Small nuclear RNA involved in splicing."),
        # Variant types
        VocabularyTerm(id="SO:0001483", label="SNV", parents=["SO:0001059"], synonyms=["single nucleotide variant", "SNP"], definition="A single nucleotide change."),
        VocabularyTerm(id="SO:0000159", label="deletion", parents=["SO:0001059"], definition="Removal of one or more nucleotides."),
        VocabularyTerm(id="SO:0000667", label="insertion", parents=["SO:0001059"], definition="Addition of one or more nucleotides."),
        VocabularyTerm(id="SO:0001059", label="sequence_alteration", parents=["SO:0000110"], children=["SO:0001483", "SO:0000159", "SO:0000667"], definition="A change in the sequence."),
        # Exon / Intron
        VocabularyTerm(id="SO:0000147", label="exon", parents=["SO:0000001"], definition="A region of a transcript that is not removed by splicing.", relationships={"part_of": ["SO:0000234"]}),
        VocabularyTerm(id="SO:0000188", label="intron", parents=["SO:0000001"], definition="A region of a transcript that is removed by splicing.", relationships={"adjacent_to": ["SO:0000147"]}),
    ]


def get_toy_rag_terms() -> list[VocabularyTerm]:
    """~15 terms mimicking Gene Ontology (for semantic search testing)."""
    return [
        VocabularyTerm(id="GO:0008150", label="biological_process", definition="A biological objective to which the gene product contributes."),
        VocabularyTerm(id="GO:0009987", label="cellular process", parents=["GO:0008150"], definition="Any process carried out at the cellular level."),
        VocabularyTerm(id="GO:0006915", label="apoptotic process", parents=["GO:0009987"], synonyms=["programmed cell death", "apoptosis"], definition="A form of programmed cell death."),
        VocabularyTerm(id="GO:0006954", label="inflammatory response", parents=["GO:0009987"], synonyms=["inflammation"], definition="The response to an inflammatory stimulus.", relationships={"part_of": ["GO:0006952"]}),
        VocabularyTerm(id="GO:0006952", label="defense response", parents=["GO:0009987"], definition="Reactions triggered in response to the presence of a foreign body."),
        VocabularyTerm(id="GO:0007049", label="cell cycle", parents=["GO:0009987"], definition="The progression of events in a cell from division to division."),
        VocabularyTerm(id="GO:0007067", label="mitotic nuclear division", parents=["GO:0007049"], synonyms=["mitosis"], definition="Nuclear division as part of the mitotic cell cycle."),
        VocabularyTerm(id="GO:0006281", label="DNA repair", parents=["GO:0009987"], definition="The process of restoring DNA to its correct sequence and/or structure."),
        VocabularyTerm(id="GO:0003674", label="molecular_function", definition="Activities at the molecular level carried out by gene products."),
        VocabularyTerm(id="GO:0003677", label="DNA binding", parents=["GO:0003674"], synonyms=["DNA-binding"], definition="Interacting selectively with DNA."),
        VocabularyTerm(id="GO:0016301", label="kinase activity", parents=["GO:0003674"], definition="Catalysis of the transfer of a phosphate group."),
        VocabularyTerm(id="GO:0005575", label="cellular_component", definition="A location relative to cellular structures."),
        VocabularyTerm(id="GO:0005634", label="nucleus", parents=["GO:0005575"], definition="A membrane-bounded organelle containing the chromosomes."),
        VocabularyTerm(id="GO:0005737", label="cytoplasm", parents=["GO:0005575"], definition="The contents of a cell excluding the plasma membrane and nucleus."),
        VocabularyTerm(id="GO:0005886", label="plasma membrane", parents=["GO:0005575"], synonyms=["cell membrane"], definition="The membrane surrounding the cell."),
    ]
