#!/bin/bash -eu
set -o pipefail

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

VOCAB_DIR="${PROJECT_DIR}/data/vocabularies"
mkdir -p "${VOCAB_DIR}"

download() {
    local name="$1"
    local url="$2"
    local output="$3"

    if [ -f "${output}" ]; then
        return
    fi

    printf "%-30s %s\n" "${name}" "${url}"
    if ! curl -fsSL --max-time 300 -o "${output}" "${url}" 2>/dev/null; then
        echo "  FAILED: ${name}"
        rm -f "${output}"
        return 1
    fi
}

download_zip() {
    local name="$1"
    local url="$2"
    local output="$3"
    local inner_file="${4:-}"

    if [ -f "${output}" ]; then
        return
    fi

    local tmpzip="${VOCAB_DIR}/_tmp_${name}.zip"
    printf "%-30s %s\n" "${name}" "${url}"
    if ! curl -fsSL --max-time 300 -o "${tmpzip}" "${url}" 2>/dev/null; then
        echo "  FAILED: ${name}"
        rm -f "${tmpzip}"
        return 1
    fi

    if [ -n "${inner_file}" ]; then
        unzip -p "${tmpzip}" "${inner_file}" > "${output}" 2>/dev/null || unzip -p "${tmpzip}" > "${output}" 2>/dev/null
    else
        local tmpdir="${VOCAB_DIR}/_tmp_${name}"
        mkdir -p "${tmpdir}"
        unzip -qo "${tmpzip}" -d "${tmpdir}" 2>/dev/null
        # Move extracted content next to output
        mv "${tmpdir}"/* "$(dirname "${output}")/" 2>/dev/null || true
        rm -rf "${tmpdir}"
    fi
    rm -f "${tmpzip}"
}

# --- OBO ontologies (direct downloads from OBO Foundry) ---

download "Sequence Ontology" \
    "http://purl.obolibrary.org/obo/so.obo" \
    "${VOCAB_DIR}/so.obo" || true

download "Cell Ontology" \
    "http://purl.obolibrary.org/obo/cl.obo" \
    "${VOCAB_DIR}/cl.obo" || true

download "Gene Ontology" \
    "http://purl.obolibrary.org/obo/go.obo" \
    "${VOCAB_DIR}/go.obo" || true

download "Disease Ontology" \
    "http://purl.obolibrary.org/obo/doid.obo" \
    "${VOCAB_DIR}/doid.obo" || true

download "Human Phenotype Ontology" \
    "http://purl.obolibrary.org/obo/hp.obo" \
    "${VOCAB_DIR}/hp.obo" || true

download "ChEBI" \
    "http://purl.obolibrary.org/obo/chebi.obo" \
    "${VOCAB_DIR}/chebi.obo" || true

download "NCI Thesaurus" \
    "http://purl.obolibrary.org/obo/ncit.obo" \
    "${VOCAB_DIR}/ncit.obo" || true

# --- OWL ontologies ---

download "OBI" \
    "http://purl.obolibrary.org/obo/obi.owl" \
    "${VOCAB_DIR}/obi.owl" || true

download "EFO" \
    "http://www.ebi.ac.uk/efo/efo.owl" \
    "${VOCAB_DIR}/efo.owl" || true

# --- Tabular / JSON ---

download "HGNC" \
    "https://ftp.ebi.ac.uk/pub/databases/genenames/hgnc/tsv/hgnc_complete_set.txt" \
    "${VOCAB_DIR}/hgnc_complete_set.txt" || true

download "Ensembl Biotypes" \
    "https://raw.githubusercontent.com/Ensembl/ensembl/release/113/modules/Bio/EnsEMBL/Biotype.pm" \
    "${VOCAB_DIR}/ensembl_biotypes_raw.pm" || true

# Generate Ensembl biotypes JSON from hardcoded list (stable, rarely changes)
if [ ! -f "${VOCAB_DIR}/ensembl_biotypes.json" ]; then
    python3 -c "
import json
biotypes = [
    {'id': 'protein_coding', 'label': 'Protein coding', 'definition': 'Gene/transcript that contains an open reading frame (ORF)'},
    {'id': 'lncRNA', 'label': 'Long non-coding RNA', 'definition': 'Non-coding RNA longer than 200 nucleotides'},
    {'id': 'miRNA', 'label': 'MicroRNA', 'definition': 'Small non-coding RNA (~22nt) involved in post-transcriptional gene regulation'},
    {'id': 'snRNA', 'label': 'Small nuclear RNA', 'definition': 'Small RNA involved in RNA splicing'},
    {'id': 'snoRNA', 'label': 'Small nucleolar RNA', 'definition': 'Small RNA involved in rRNA modification'},
    {'id': 'rRNA', 'label': 'Ribosomal RNA', 'definition': 'RNA component of the ribosome'},
    {'id': 'tRNA', 'label': 'Transfer RNA', 'definition': 'RNA that transfers amino acids during translation'},
    {'id': 'misc_RNA', 'label': 'Miscellaneous RNA', 'definition': 'Non-coding RNA that cannot be classified'},
    {'id': 'scRNA', 'label': 'Small cytoplasmic RNA', 'definition': 'Small RNA found in the cytoplasm'},
    {'id': 'scaRNA', 'label': 'Small Cajal body RNA', 'definition': 'RNA localized to Cajal bodies'},
    {'id': 'pseudogene', 'label': 'Pseudogene', 'definition': 'Gene that has lost its ability to code for a protein'},
    {'id': 'processed_pseudogene', 'label': 'Processed pseudogene', 'definition': 'Pseudogene arising from retrotransposition'},
    {'id': 'unprocessed_pseudogene', 'label': 'Unprocessed pseudogene', 'definition': 'Pseudogene arising from gene duplication'},
    {'id': 'transcribed_pseudogene', 'label': 'Transcribed pseudogene', 'definition': 'Pseudogene with transcription evidence'},
    {'id': 'IG_C_gene', 'label': 'Immunoglobulin C gene', 'definition': 'Constant chain immunoglobulin gene'},
    {'id': 'IG_D_gene', 'label': 'Immunoglobulin D gene', 'definition': 'Diversity immunoglobulin gene'},
    {'id': 'IG_J_gene', 'label': 'Immunoglobulin J gene', 'definition': 'Joining chain immunoglobulin gene'},
    {'id': 'IG_V_gene', 'label': 'Immunoglobulin V gene', 'definition': 'Variable chain immunoglobulin gene'},
    {'id': 'TR_C_gene', 'label': 'T cell receptor C gene', 'definition': 'Constant chain T cell receptor gene'},
    {'id': 'TR_D_gene', 'label': 'T cell receptor D gene', 'definition': 'Diversity T cell receptor gene'},
    {'id': 'TR_J_gene', 'label': 'T cell receptor J gene', 'definition': 'Joining chain T cell receptor gene'},
    {'id': 'TR_V_gene', 'label': 'T cell receptor V gene', 'definition': 'Variable chain T cell receptor gene'},
    {'id': 'ribozyme', 'label': 'Ribozyme', 'definition': 'RNA with catalytic activity'},
    {'id': 'vault_RNA', 'label': 'Vault RNA', 'definition': 'Short non-coding RNA associated with vault complex'},
    {'id': 'Y_RNA', 'label': 'Y RNA', 'definition': 'Small non-coding RNA component of Ro ribonucleoprotein'},
    {'id': 'Mt_tRNA', 'label': 'Mitochondrial tRNA', 'definition': 'Transfer RNA located in mitochondrial genome'},
    {'id': 'Mt_rRNA', 'label': 'Mitochondrial rRNA', 'definition': 'Ribosomal RNA located in mitochondrial genome'},
    {'id': 'TEC', 'label': 'To be experimentally confirmed', 'definition': 'Locus awaiting experimental confirmation'},
    {'id': 'nonsense_mediated_decay', 'label': 'Nonsense mediated decay', 'definition': 'Transcript predicted to undergo nonsense-mediated decay'},
    {'id': 'non_stop_decay', 'label': 'Non-stop decay', 'definition': 'Transcript lacking a stop codon'},
    {'id': 'retained_intron', 'label': 'Retained intron', 'definition': 'Transcript containing a retained intron'},
    {'id': 'protein_coding_CDS_not_defined', 'label': 'Protein coding CDS not defined', 'definition': 'Protein coding gene with no defined CDS'},
    {'id': 'artifact', 'label': 'Artifact', 'definition': 'Annotation determined to be an artifact'},
]
with open('${VOCAB_DIR}/ensembl_biotypes.json', 'w') as f:
    json.dump(biotypes, f, indent=2)
"
    rm -f "${VOCAB_DIR}/ensembl_biotypes_raw.pm"
fi

# --- GMT (pathway databases) ---

# WikiPathways: find the latest GMT file for Homo sapiens
if [ ! -f "${VOCAB_DIR}/wikipathways.gmt" ]; then
    wp_url=$(curl -fsSL "https://data.wikipathways.org/current/gmt/" 2>/dev/null \
        | grep -oP 'href="[^"]*Homo_sapiens\.gmt"' | head -1 | sed 's/href="//;s/"$//' || true)
    if [ -n "${wp_url}" ]; then
        download "WikiPathways" "https://data.wikipathways.org/current/gmt/${wp_url}" "${VOCAB_DIR}/wikipathways.gmt" || true
    fi
fi

download "Reactome" \
    "https://reactome.org/download/current/ReactomePathways.gmt.zip" \
    "${VOCAB_DIR}/reactome.gmt.zip" || true

# Extract Reactome GMT
if [ -f "${VOCAB_DIR}/reactome.gmt.zip" ] && [ ! -f "${VOCAB_DIR}/reactome.gmt" ]; then
    unzip -p "${VOCAB_DIR}/reactome.gmt.zip" > "${VOCAB_DIR}/reactome.gmt" 2>/dev/null || true
    rm -f "${VOCAB_DIR}/reactome.gmt.zip"
fi

# Fallback: try non-zip Reactome if zip failed
if [ ! -f "${VOCAB_DIR}/reactome.gmt" ]; then
    download "Reactome (plain)" \
        "https://reactome.org/download/current/ReactomePathways.gmt" \
        "${VOCAB_DIR}/reactome.gmt" || true
fi

# --- FDA datasets ---

download "NDC" \
    "https://download.open.fda.gov/drug/ndc/drug-ndc-0001-of-0001.json.zip" \
    "${VOCAB_DIR}/ndc.json.zip" || true

if [ -f "${VOCAB_DIR}/ndc.json.zip" ] && [ ! -f "${VOCAB_DIR}/ndc.json" ]; then
    unzip -p "${VOCAB_DIR}/ndc.json.zip" > "${VOCAB_DIR}/ndc.json" 2>/dev/null || true
    rm -f "${VOCAB_DIR}/ndc.json.zip"
fi

# UNII: FDA substance registry (may require manual download if URL changes)
download "UNII" \
    "https://fdasis.nlm.nih.gov/srs/download/srs/UNII_Data.zip" \
    "${VOCAB_DIR}/unii.zip" || true

if [ -f "${VOCAB_DIR}/unii.zip" ] && [ ! -f "${VOCAB_DIR}/unii.tsv" ]; then
    unzip -qo "${VOCAB_DIR}/unii.zip" -d "${VOCAB_DIR}/" 2>/dev/null || true
    # Rename extracted file if needed
    for f in "${VOCAB_DIR}"/UNII_*.txt "${VOCAB_DIR}"/UNII_*.tsv; do
        if [ -f "$f" ]; then
            mv "$f" "${VOCAB_DIR}/unii.tsv" 2>/dev/null || true
            break
        fi
    done
    rm -f "${VOCAB_DIR}/unii.zip"
fi

# --- MeSH XML ---

download "MeSH" \
    "https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2025.xml" \
    "${VOCAB_DIR}/mesh_desc.xml" || true

# --- Skipped (require license/account) ---
# SNOMED-CT: Requires UMLS license
# RxNorm: Requires UMLS license
# CDISC: Requires CDISC membership
# NCBI Taxonomy: Very large (2.4M terms), download manually if needed

echo "Done. Files in ${VOCAB_DIR}:"
ls -lhS "${VOCAB_DIR}/" 2>/dev/null | grep -v "^total"
