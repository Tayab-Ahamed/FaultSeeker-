# Batch A adapter fix 3 — read-only jobs

## Job 1 — commit 70d1b09 scope

- Benchmark rows audited: 110 successful rows
- Affected rows: 67
- Affected rows replayable from full local trace + RPC artifacts: 2
- Affected rows missing full local traces: 65

| Reading | R@1 | R@3 | R@5 | N |
| --- | ---: | ---: | ---: | ---: |
| Archival ranks at 240fd9f | 0/110 (0.000000) | 0/110 (0.000000) | 0/110 (0.000000) | 110 |
| Current stored ranks after 70d1b09 | 25/110 (0.227273) | 49/110 (0.445455) | 52/110 (0.472727) | 110 |
| Producer replay, partial sample | 0/2 (0.000000) | 0/2 (0.000000) | 0/2 (0.000000) | 2 |

### Affected rows

| Transaction | Chain | Archival rank | Rank after 70d1b09 | Changed stored fields | Full local trace? |
| --- | --- | ---: | ---: | --- | --- |
| `0x07e5568b71f1f4d9234d5925473c598865c5ee1800348c1c4b044c6f0223f308` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x09925028ce5d6a54801d04ff8f39e79af6c24289e84b301ddcdb6adfa51e901b` | bsc | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x0b062361e16a2ea0942cc1b4462b6584208c8c864609ff73aaa640aaa2d92428` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x0fc5c0d41e5506fdb9434fab4815a4ff671afc834e47a533b3bed7182ece73b0` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x1106418384414ed56cd7cbb9fedc66a02d39b663d580abc618f2d387348354ab` | eth | None | 7 | first_hit_rank | False |
| `0x1194e1d6085885ce054a7ff8cd3cd0c3fa308ec87e4ccde8dd0549842fef4f1b` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x138daa4cbeaa3db42eefcec26e234fc2c89a4aa17d6b1870fc460b2856fd11a6` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x19c04bc04ee8117abfdf0c9301787b12b27f3c5c13308b4f66711a8f0ecacc62` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x1ea0a2e88efceccb2dd93e6e5cb89e5421666caeefb1e6fc41b68168373da342` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x20ecd8310a2cc7f7774aa5a045c8a99ad84a8451d6650f24e0911e9f4355b13a` | bsc | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x21d8b164f0cb8beb1ed27d164ed986c3fc26b33655ce18226b05b9cfcf6cd93c` | bsc | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x23fcf9d4517f7cc39815b09b0a80c023ab2c8196c826c93b4100f2e26b701286` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x24a68d2a4bbb02f398d3601acfd87b09f543d935fc24862c314aaf64c295acdb` | bsc | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x256979ae169abb7fbbbbc14188742f4b9debf48b48ad5b5207cadcc99ccb493b` | eth | None | 5 | first_hit_rank, recall_at_5 | False |
| `0x2606d459a50ca4920722a111745c2eeced1d8a01ff25ee762e22d5d4b1595739` | eth | None | 4 | first_hit_rank, recall_at_5 | False |
| `0x2881e839d4d562fad5356183e4f6a9d427ba6f475614ce8ef64dbfe557a4a2cc` | eth | None | 6 | first_hit_rank | False |
| `0x2e832f044b4a0a0b8d38166fe4d781ab330b05b9efa9e72a7a0895f1b984084b` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x33479bcfbc792aa0f8103ab0d7a3784788b5b0e1467c81ffbed1b7682660b4fa` | eth | None | 3 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x3bba4fb6de00dd38df3ad68e51c19fe575a95a296e0632028f101c5199b6f714` | eth | None | 4 | first_hit_rank, recall_at_5 | False |
| `0x3c09c6306b67737227edc24c663462d870e7c2bf39e9ab66877a980c900dd5d5` | eth | None | 3 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x3d163bfbec5686d428a6d43e45e2626a220cc4fcfac7620c620b82c1f2537c78` | eth | None | 18 | first_hit_rank | False |
| `0x3ed75df83d907412af874b7998d911fdf990704da87c2b1a8cf95ca5d21504cf` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x3f1973fe56de5ecd59a815d3b14741cf48385903b0ccfe248f7f10c2765061f7` | bsc | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x44aad3b853866468161735496a5d9cc961ce5aa872924c5d78673076b1cd95aa` | eth | None | 12 | first_hit_rank | False |
| `0x46deef0f52e3a983b67abf4714448a41dd7ffd6d32d32da69d62081c68ad7882` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x485e08dc2b6a4b3aeadcb89c3d18a37666dc7d9424961a2091d6b3696792f0f3` | eth | None | 10 | first_hit_rank | False |
| `0x48d22ea24c1ae707b8b17ca2a3ea81a1aee64a075d93e5bff81a7370e2cacea7` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x491cf8b2a5753fdbf3096b42e0a16bc109b957dc112d6537b1ed306e483d0744` | eth | None | 3 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x4e5bb7e3f552f5ee6ee97db9a9fcf07287aae9a1974e24999690855741121aff` | bsc | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x597d11c05563611cb4ad4ed4c57ca53bbe3b7d3fefc37d1ef0724ad58904742b` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x6200bf5c43c214caa1177c3676293442059b4f39eb5dbae6cfd4e6ad16305668` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x6439d63cc57fb68a32ea8ffd8f02496e8abad67292be94904c0b47a4d14ce90d` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x6bfd9e286e37061ed279e4f139fbc03c8bd707a2cdd15f7260549052cbba79b7` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x72a252277e30ea6a37d2dc9905c280f3bc389b87f72b81a59aa8f50baebd8eaa` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x7604c7dd6e9bcdba8bac277f1f8e7c1e4c6bb57afd4ddf6a16f629e8495a0281` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x800a5b3178f680feebb81af69bd3dff791b886d4ce31615e601f2bb1f543bb2e` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x8c3f442fc6d640a6ff3ea0b12be64f1d4609ea94edd2966f42c01cd9bdcf04b5` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0x8e1b0ab098c4cc5f632e00b0842b5f825bbd15ded796d4a59880bb724f6c5372` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x90b468608fbcc7faef46502b198471311baca3baab49242a4a85b73d4924379b` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0x90fb0c9976361f537330a5617a404045ffb3fef5972cf67b531386014eeae7a9` | eth | None | 10 | first_hit_rank | False |
| `0x958236266991bc3fe3b77feaacea120f172c0708ad01c7a715b255f218f9313c` | eth | None | 19 | first_hit_rank | True |
| `0x9f4ef3cc55b016ea6b867807a09f80d1b2e36f6cd6fccfaf0182f46060332c57` | bsc | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0xa4e650772f6e6b7ecc0964fe4c3854850669d1467570a2fa2b6edfa0f112c4b7` | eth | None | 9 | first_hit_rank | False |
| `0xa6f63fcb6bec8818864d96a5b1bb19e8bd85ee37b2cc916412e720988440b2aa` | eth | None | 7 | first_hit_rank | True |
| `0xa992b28ecf2eed778d20d5200946ea341b950be0c3d78b1f2237a4d8d795de95` | eth | None | 3 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0xac7292e7d0ec8ebe1c94203d190874b2aab30592327b6cc875d00f18de6f3133` | eth | None | 3 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0xb61413c495fdad6114a7aa863a00b2e3c28945979a10885b12b30316ea9f072c` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0xc0be8c3792a5b1ba7d653dc681ff611a5b79a75fe51c359cf1aac633e9441574` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0xc18ec2eb7d41638d9982281e766945d0428aaeda6211b4ccb6626ea7cff31f4a` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0xc9b2cbc1437bbcd8c328b6d7cdbdae33d7d2a9ef07eca18b4922aac0430991e7` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0xcf834aff4de9992f5da9c443600dad9c6277a8a00de5007842fece51564992db` | eth | None | 6 | first_hit_rank | False |
| `0xd493c73397952049644c531309df3dd4134bf3db1e64eb6f0b68b016ee0bffde` | eth | None | 14 | first_hit_rank | False |
| `0xd5b4d68432cbbd912130bbb5b93399031ddbb400d8f723c78050574de7533106` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0xd9156f507c701a09d3312e1987383c7c882df50b3127e1adfd74d74052642114` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0xd927843e30c6b2bf43103d83bca6abead648eac3cad0d05b1b0eb84cd87de9b6` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0xda8f6a4bed7e5689a343d111632d37480c0316f1d20b732803c4bd482823e284` | eth | None | 11 | first_hit_rank | False |
| `0xdaccbc437cb07427394704fbcc8366589ffccf974ec6524f3483844b043f31d5` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0xe4db1550e3aa78a05e93bfd8fbe21b6eba5cce50dc06688949ab479ebed18048` | bsc | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0xeaef2831d4d6bca04e4e9035613be637ae3b0034977673c1c2f10903926f29c0` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0xeb8c3bebed11e2e4fcd30cbfc2fb3c55c4ca166003c7f7d319e78eaab9747098` | eth | None | 13 | first_hit_rank | False |
| `0xf0a13b445674094c455de9e947a25bade75cac9f5176695fca418898ea25742f` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0xf1818f62c635e5c80ef16b7857da812c74ce330ebed46682b4d173bffe84c666` | eth | None | 8 | first_hit_rank | False |
| `0xf4a3d0e01bbca6c114954d4a49503fc94dfdbc864bded5530b51a207640d86b5` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0xf72f1d10fc6923f87279ce6c0aef46e372c6652a696f280b0465a301a92f2e26` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |
| `0xfc872bf5ca8f04b18b82041ec563e4abf2e31e1fc27d1ea5dee39bc8a79d2d06` | eth | None | 2 | first_hit_rank, recall_at_3, recall_at_5 | False |
| `0xfe8bc757d87e97a5471378c90d390df47e1b29bb9fca918b94acd8ecfaadc598` | eth | None | 13 | first_hit_rank | False |
| `0xfeedbf51b4e2338e38171f6e19501327294ab1907ab44cfd2d7e7336c975ace7` | eth | None | 1 | first_hit_rank, recall_at_1, recall_at_3, recall_at_5 | False |

## Job 2 — Batch A producer-era field check

- Valid records: 23
- Identity/trace fields present: True
- Required RPC-normalized transaction and receipt payloads present: False
- Batch A replay executed: False

The 23 valid-set records contain transaction_hash, chain, and a callTracer trace, but no per-record transaction/receipt payload. The producer-era ForensicsOrchestrator path requires those RPC-normalized inputs through TransactionInfoCollector.
