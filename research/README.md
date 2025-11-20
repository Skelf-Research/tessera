# CallDNS Research Paper

This directory contains the academic research paper on CallDNS: Zero-Knowledge Caller Verification for Privacy-Preserving Telecommunications in Financial Services.

## Files

- **calldns_paper.tex**: LaTeX source file for the complete research paper
- **README.md**: This file

## Compiling the Paper

To compile the LaTeX document to PDF:

```bash
cd docs/paper
pdflatex calldns_paper.tex
pdflatex calldns_paper.tex  # Run twice to resolve references
```

Or use any LaTeX editor (Overleaf, TeXShop, etc.)

## Paper Structure

The paper consists of the following sections:

1. **Abstract**: Overview of CallDNS system and contributions
2. **Introduction**: Problem statement, challenges in telecommunications security, and financial services context
3. **Background and Related Work**: Review of telecommunications security, zero-knowledge proofs, privacy-preserving communications, and financial services security
4. **Threat Model and Requirements**: Adversary capabilities, security requirements, and privacy requirements
5. **System Architecture**: Detailed technical architecture including cryptographic protocol, network distribution, privacy mechanisms, and SDK design
6. **Security Analysis**: Formal security proofs and privacy analysis
7. **Applications in Financial Services**: Detailed use cases in banking, trading, wealth management, insurance, and regulatory compliance
8. **Implementation**: Technical implementation details for cryptography, networking, SDKs, key management, and testing
9. **Discussion**: Performance analysis, usability considerations, limitations, and future work
10. **Conclusion**: Summary of contributions and broader impact

## Key Contributions

The paper presents:

- Decentralized zero-knowledge caller verification protocol based on Schnorr signatures
- Commitment-based proof distribution with Bloom filter anonymity
- Traffic analysis resistance through padding, cover traffic, and timing obfuscation
- Cross-platform SDK implementations for practical deployment
- Formal security and privacy analysis
- Comprehensive financial services applications and use cases

## Citation

```bibtex
@article{sarkar2025calldns,
  title={CallDNS: Zero-Knowledge Caller Verification for Privacy-Preserving Telecommunications in Financial Services},
  author={Sarkar, Dipankar},
  journal={arXiv preprint},
  year={2025}
}
```

## Author

Dipankar Sarkar

## References

The paper includes 40+ academic references covering cryptography, telecommunications security, privacy-preserving systems, and financial services applications, all published before early 2025.
