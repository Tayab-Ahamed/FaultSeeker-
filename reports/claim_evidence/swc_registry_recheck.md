# SWC Registry Recheck

Source text checked: the SWC Registry README at
`https://raw.githubusercontent.com/SmartContractSecurity/SWC-registry/master/README.md`.
The README states that SWCs classify weaknesses identifiable within Solidity
smart-contract code and do not cover smart-contract-adjacent weaknesses.

Offline review of all 46 previously unmapped label strings against that scope
and the registry titles already retained in the cohort produced:

```text
previously_unmapped_labels=46
new_swc_ids_assigned=0
no_swc_equivalent=46
reasons_present=46
```

Economic/oracle manipulation, flash-loan technique, tokenomics, protocol
business logic, generic validation/access-control labels, social engineering,
and placeholder labels were not forced into unrelated SWC entries.
