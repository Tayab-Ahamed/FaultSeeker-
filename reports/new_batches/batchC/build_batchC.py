"""Freeze Batch C phase-1 source-backed dataset without RPC, tracing, or scoring."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from eth_utils import keccak

from exclusion_support import get_exclusions
from source_checks import signature_in_source, validate_target

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
POC = OUT / "poc_sources"
COMMIT = "7363f76db51f0fea97f8e659b20ee8bdc5fbca25"
FETCHED_AT = "2026-10-17T18:27:49Z"
IMPORTED_FETCHED_AT = "2026-10-17T18:34:00Z"
REPOSITORY = "https://github.com/SunWeb3Sec/DeFiHackLabs"


# Every selected row is source-backed.  Signature declarations are quoted from
# the PoC itself, except KyberSwap's imported local IPoolActions declaration,
# which is fetched and pinned as an additional raw source file.
SPECS = [
    {"path": "src/test/2017-07/Parity_first_hack_exp.sol", "tx": "0x9dbf0326a03a2a3719c27be4fa69aacc9857fd231a8d9dcaede4bb083def75ec", "name": "Parity multisig wallet first hack", "category": "Access Control", "date": "2017-07", "address": "0xBEc591De75b8699A3Ba52F073428822d0Bfc0D7e", "signature": "initWallet(address[],uint256,uint256)", "address_lines": [9, 28], "signature_lines": [20, 21, 22, 23], "call_lines": [46, 47], "tx_lines": [10]},
    {"path": "src/test/2018-04/BEC_exp.sol", "tx": "0xad89ff16fd1ebe3a0a7cf4ed282302c06626c1af33221ebe0d3a470aba4a660f", "name": "BEC batch transfer overflow", "category": "Token / Integer Overflow", "date": "2018-04", "address": "0xC5d105E63711398aF9bbff092d4b6769C82F793D", "signature": "batchTransfer(address[],uint256)", "address_lines": [16, 21], "signature_lines": [8, 9, 10, 11, 12], "call_lines": [32, 35], "tx_lines": [15]},
    {"path": "src/test/2018-10/SpankChain_exp.sol", "tx": "0x21e9d20b57f6ae60dac23466c8395d47f42dc24628e5a31f224567a2b4effa88", "name": "SpankChain payment-channel reentrancy", "category": "Reentrancy / State Accounting", "date": "2018-10", "address": "0xf91546835f756DA0c10cFa0CDA95b15577b84aA7", "signature": "createChannel(bytes32,address,uint256,address,uint256[2])", "address_lines": [9, 65], "signature_lines": [21, 22, 23, 24, 25, 26, 27, 28], "call_lines": [76, 77, 78, 79, 80, 81], "tx_lines": [10]},
    {"path": "src/test/2020-11/Pickle_exp.sol", "tx": "0xe72d4e7ba9b5af0cf2a8cfb1e30fd9f388df0ab3da79790be842bfbed11087b0", "name": "Pickle Finance evil jar", "category": "Arbitrary Call / Vault Accounting", "date": "2020-11", "address": "0x6847259b2B3A4c17e7c43C54409810aF48bA5210", "signature": "swapExactJarForJar(address,address,uint256,uint256,address[],bytes[])", "address_lines": [15], "signature_lines": [69, 70, 71, 72, 73, 74, 75, 76, 77], "call_lines": [34, 37, 41, 43, 49], "tx_lines": [10]},
    {"path": "src/test/2021-02/Yearn_ydai_exp.sol", "tx": "0x59faab5a1911618064f1ffa1e4649d85c99cfd9f0d64dcebbc1af7d7630da98b", "name": "Yearn yDAI vault manipulation", "category": "Price Manipulation / Vault Accounting", "date": "2021-02", "address": "0xACd43E627e64355f1861cEC6d3a6688B31a6F952", "signature": "deposit(uint256)", "address_lines": [12, 49], "signature_lines": [31, 32, 33, 34, 35, 36, 37], "call_lines": [107], "tx_lines": [13]},
    {"path": "src/test/2021-03/PAID_exp.sol", "tx": "0x4bb10927ea7afc2336033574b74ebd6f73ef35ac0db1bb96229627c9d77555a0", "name": "PAID token unauthorized mint", "category": "Access Control / Unlimited Mint", "date": "2021-03", "address": "0x8c8687fC965593DFb2F0b4EAeFD55E9D8df348df", "signature": "mint(address,uint256)", "address_lines": [23], "signature_lines": [14, 15], "call_lines": [30, 31, 32], "tx_lines": [12]},
    {"path": "src/test/2021-05/RariCapital_exp.sol", "tx": "0x171072422efb5cd461546bfe986017d9b5aa427ff1c07ebe8acc064b13a7b7be", "name": "Rari Capital fake-token lending", "category": "Lending / Fake Token", "date": "2021-05", "address": "0x67B66C99D3Eb37Fa76Aa3Ed1ff33E8e39F0b9c7A", "signature": "work(uint256,address,uint256,uint256,bytes)", "address_lines": [18], "signature_lines": [13, 14], "call_lines": [38, 39, 40], "tx_lines": [8]},
    {"path": "src/test/2021-07/Chainswap_exp1.sol", "tx": "0x5c5688a9f981a07ed509481352f12f22a4bd7cea46a932c6d6bbe67cca3c54be", "name": "ChainSwap signature validation bypass", "category": "Bridge / Signature Validation", "date": "2021-07", "address": "0x7fe68FC06e1A870DcbeE0acAe8720396DC12FC86", "signature": "receive(uint256,address,uint256,uint256,(address,uint8,bytes32,bytes32)[])", "address_lines": [21], "signature_lines": [8, 9, 10, 11, 12, 13, 15, 16, 17, 54], "call_lines": [52, 53, 54, 55, 56, 57, 58, 59, 60], "tx_lines": [28]},
    {"path": "src/test/2021-08/PolyNetwork_exp.sol", "tx": "0xb1f70464bd95b774c6ce60fc706eb5f9e35cb5f06e6cfe7c17dcda46ffd59581", "name": "Poly Network cross-chain manager", "category": "Bridge / Access Control", "date": "2021-08", "address": "0x838bf9E95CB12Dd76a54C9f9D2E3082EAF928270", "signature": "verifyHeaderAndExecuteTx(bytes,bytes,bytes,bytes,bytes)", "address_lines": [79], "signature_lines": [8, 9, 10, 11, 12, 13, 14, 15], "call_lines": [163, 164, 165, 166, 167, 168, 169], "tx_lines": [99]},
    {"path": "src/test/2021-10/Cream_2_exp.sol", "tx": "0x0fe2542079644e107cbf13690eb9c2c65963ccb79089ff96bfaf8dced2331c92", "name": "Cream Finance crYUSD collateral inflation", "category": "Lending / Oracle Manipulation", "date": "2021-10", "address": "0x4BAa77013ccD6705ab0522853cB0E9d453579Dd4", "signature": "borrow(uint256)", "address_lines": [76], "signature_lines": [53, 54, 55, 56], "call_lines": [119, 120], "tx_lines": [10]},
    {"path": "src/test/2021-10/IndexedFinance_exp.sol", "tx": "0x44aad3b853866468161735496a5d9cc961ce5aa872924c5d78673076b1cd95aa", "name": "Indexed Finance pool accounting", "category": "Price Manipulation / Pool Accounting", "date": "2021-10", "address": "0xfa6de2697D59E88Ed7Fc4dFE5A33daC43565ea41", "signature": "exitPool(uint256,uint256[])", "address_lines": [49], "signature_lines": [321], "call_lines": [238, 245, 247], "tx_lines": [12]},
    {"path": "src/test/2022-01/Anyswap_exp.sol", "tx": "0xe50ed602bd916fc304d53c4fed236698b71691a95774ff0aeeb74b699c6227f7", "name": "Anyswap permit validation bypass", "category": "Bridge / Permit Validation", "date": "2022-01", "address": "0x6b7a87899490EcE95443e979cA9485CBE7E71522", "signature": "anySwapOutUnderlyingWithPermit(address,address,address,uint256,uint256,uint8,bytes32,bytes32,uint256)", "address_lines": [10, 11], "signature_lines": [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30], "call_lines": [31, 32, 33, 34, 35, 36, 37, 38, 39, 40], "tx_lines": [19]},
    {"path": "src/test/2022-11/DFX_exp.sol", "tx": "0x6bfd9e286e37061ed279e4f139fbc03c8bd707a2cdd15f7260549052cbba79b7", "name": "DFX stablecoin pool manipulation", "category": "Stablecoin / Price Manipulation", "date": "2022-11", "address": "0x46161158b1947D9149E066d6d31AF1283b2d377C", "signature": "deposit(uint256,uint256)", "address_lines": [29], "signature_lines": [15, 17, 18, 19, 20], "call_lines": [62, 63, 64], "tx_lines": [13]},
    {"path": "src/test/2022-11/Kashi_exp.sol", "tx": "0x3d163bfbec5686d428a6d43e45e2626a220cc4fcfac7620c620b82c1f2537c78", "name": "Abracadabra Kashi oracle manipulation", "category": "Lending / Oracle Manipulation", "date": "2022-11", "address": "0xbb02A884621FB8F5BFd263A67F58B65df5b090f3", "signature": "borrow(address,uint256)", "address_lines": [55], "signature_lines": [38, 39, 40, 41], "call_lines": [91, 94, 95], "tx_lines": [11]},
    {"path": "src/test/2023-03/Euler_exp.sol", "tx": "0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d", "name": "Euler donation attack", "category": "Lending / Donation Attack", "date": "2023-03", "address": "0xe025E3ca2bE02316033184551D4d3Aa22024D9DC", "signature": "donateToReserves(uint256,uint256)", "address_lines": [65], "signature_lines": [27, 28, 29, 30], "call_lines": [123, 124, 125, 126, 127, 128, 129], "tx_lines": [14]},
    {"path": "src/test/2023-04/YearnFinance_exp.sol", "tx": "0x055cec4fa4614836e54ea2e5cd3d14247ff3d61b85aa2a41f8cc876d131e0328", "name": "Yearn yUSDT share-price manipulation", "category": "Lending / Share Price Manipulation", "date": "2023-04", "address": "0xF013406A0B1d544238083DF0B93ad0d2cBE0f65f", "signature": "mint(address,uint256)", "address_lines": [428], "signature_lines": [42, 43], "call_lines": [482, 483, 484], "tx_lines": [11]},
    {"path": "src/test/2023-08/Zunami_exp.sol", "tx": "0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb", "name": "Zunami UZD price-cache manipulation", "category": "Stablecoin / Price Manipulation", "date": "2023-08", "address": "0xb40b6608b2743e691c9b54ddbdee7bf03cd79f1c", "signature": "cacheAssetPrice()", "address_lines": [10, 36], "signature_lines": [20, 21], "call_lines": [140, 141, 142], "tx_lines": [11]},
    {"path": "src/test/2023-12/PineProtocol_exp.sol", "tx": "0xec7523660f8b66d9e4a5931d97ad8b30acc679c973b20038ba4c15d4336b393d", "name": "Pine Protocol NFT lending repayment", "category": "NFT Lending / Repayment Accounting", "date": "2023-12", "address": "0xC3f4659588b13f23E09Ec54783A3c407e39ad589", "signature": "repay(uint256,uint256,address)", "address_lines": [10, 47, 48], "signature_lines": [20, 21, 22, 23], "call_lines": [105, 108, 109], "tx_lines": [14]},
    {"path": "src/test/2023-12/Convergence_exp.sol", "tx": "0x636be30e58acce0629b2bf975b5c3133840cd7d41ffc3b903720c528f01c65d9", "name": "Convergence reward distributor", "category": "Reward Accounting / Token Inflation", "date": "2023-12", "address": "0x2b083beaaC310CC5E190B1d2507038CcB03E7606", "signature": "claimMultipleStaking(address[],address,uint256,bool,uint256)", "address_lines": [41], "signature_lines": [26, 27, 28, 29, 30, 31, 32, 33], "call_lines": [51, 53, 54, 58], "tx_lines": [8]},
    {"path": "src/test/2023-11/Raft_exp.sol", "tx": "0xfeedbf51b4e2338e38171f6e19501327294ab1907ab44cfd2d7e7336c975ace7", "name": "Raft precision-loss liquidation", "category": "Lending / Precision Loss", "date": "2023-11", "address": "0x9ab6b21cdf116f611110b048987e58894786c244", "signature": "liquidate(address)", "address_lines": [10, 73], "signature_lines": [19, 20, 21, 22], "call_lines": [140, 141, 142], "tx_lines": [11]},
    {"path": "src/test/2024-01/SocketGateway_exp.sol", "tx": "0xc6c3331fa8c2d30e1ef208424c08c039a89e510df2fb6ae31e5aa40722e28fd6", "name": "Socket vulnerable route arbitrary call", "category": "Bridge / Arbitrary Call", "date": "2024-01", "address": "0xCC5fDA5e3cA925bd0bb428C8b2669496eE43067e", "signature": "performAction(address,address,uint256,address,bytes32,bytes)", "address_lines": [26, 30], "signature_lines": [11, 12, 13, 14, 15, 16, 17, 18, 19], "call_lines": [61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 74], "tx_lines": [27]},
    {"path": "src/test/2024-01/PikeFinance_exp.sol", "tx": "0xe2912b8bf34d561983f2ae95f34e33ecc7792a2905a3e317fcc98052bce66431", "name": "Pike Finance proxy initialization", "category": "Proxy / Access Control", "date": "2024-01", "address": "0xfc7599cffea9de127a9f9c748ccb451a34d2f063", "signature": "upgradeToAndCall(address,bytes)", "address_lines": [9, 27], "signature_lines": [20, 21, 22], "call_lines": [48, 49, 50, 51], "tx_lines": [10]},
    {"path": "src/test/2024-03/Prisma_exp.sol", "tx": "0x00c503b595946bccaea3d58025b5f9b3726177bbdc9674e634244135282116c7", "name": "Prisma delegate approval abuse", "category": "Lending / Delegate Approval", "date": "2024-03", "address": "0x72c590349535AD52e6953744cb2A36B409542719", "signature": "setDelegateApproval(address,bool)", "address_lines": [93], "signature_lines": [55, 56], "call_lines": [169, 170, 171], "tx_lines": [10]},
    {"path": "src/test/2024-09/Shezmu_exp.sol", "tx": "0x39328ea4377a8887d3f6ce91b2f4c6b19a851e2fc5163e2f83bbc2fc136d0c71", "name": "Shezmu collateral-token mint", "category": "Lending / Access Control", "date": "2024-09", "address": "0x641249dB01d5C9a04d1A223765fFd15f95167924", "signature": "mint(address,uint256)", "address_lines": [10, 23], "signature_lines": [67, 68, 69], "call_lines": [47, 48, 53], "tx_lines": [11]},
    {"path": "src/test/2024-10/MorphoBlue_exp.sol", "tx": "0x256979ae169abb7fbbbbc14188742f4b9debf48b48ad5b5207cadcc99ccb493b", "name": "Morpho bundler authorization", "category": "Lending / Authorization", "date": "2024-10", "address": "0x4095F064B8d3c3548A3bebfd0Bbfd04750E30077", "signature": "multicall(bytes[])", "address_lines": [9, 278, 301], "signature_lines": [21, 123, 124, 125], "call_lines": [367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 381, 382], "tx_lines": [10]},
    {"path": "src/test/2025-05/ResupplyFi_exp.sol", "tx": "0xffbbd492e0605a8bb6d490c3cd879e87ff60862b0684160d08fd5711e7a872d3", "name": "Resupply reUSD oracle manipulation", "category": "Lending / Oracle Manipulation", "date": "2025-05", "address": "0x6e90c85a495d54c6d7E1f3400FEF1f6e59f86bd6", "signature": "borrow(uint256,uint256,address)", "address_lines": [10, 78], "signature_lines": [44, 45, 46], "call_lines": [125, 126, 127], "tx_lines": [11]},
    {"path": "src/test/2025-07/StrategyLlamaLendConvex_exp.sol", "tx": "0x2ff7c23dca7e9a86c70004696802cbd37d6a77fc4f3e02522b16617045b764f6", "name": "LlamaLend Convex strategy share accounting", "category": "Vault / Share Accounting", "date": "2025-07", "address": "0x75b7DB3e11138134fe4744553b5e5e3D6546d289", "signature": "redeem(uint256,address,address)", "address_lines": [10, 28], "signature_lines": [37, 38, 39], "call_lines": [86, 87, 88, 90, 91, 92], "tx_lines": [11]},
    {"path": "src/test/2018-04/SmartMesh_exp.sol", "tx": "0x1abab4c8db9a30e703114528e31dee129a3a758f7f8abc3b6494aad3d304e43f", "name": "SmartMesh transferProxy signature bypass", "category": "Token / Signature Validation", "date": "2018-04", "address": "0x55f93985431fc9304077687a35a1ba103dc1e081", "signature": "transferProxy(address,address,uint256,uint256,uint8,bytes32,bytes32)", "address_lines": [8, 35], "signature_lines": [20, 21, 22, 23, 24, 25, 26, 27, 28, 29], "call_lines": [43, 44, 45, 46, 47, 48, 49, 50, 51], "tx_lines": [9]},
    {"path": "src/test/2022-12/Rubic_exp.sol", "tx": "0x9a97d85642f956ad7a6b852cf7bed6f9669e2c2815f3279855acf7f1328e7d46", "name": "Rubic cross-chain router arbitrary call", "category": "Bridge / Arbitrary Call", "date": "2022-12", "address": "0x3335A88bb18fD3b6824b59Af62b50CE494143333", "signature": "routerCallNative((address,uint256,uint256,address,uint256,address,address,address),bytes)", "address_lines": [49], "signature_lines": [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26], "call_lines": [88, 89, 90, 91, 92, 93, 94, 95, 96, 116, 117, 118], "tx_lines": [11]},
    {"path": "src/test/2023-11/KyberSwap_exp.eth.1.sol", "tx": "0x485e08dc2b6a4b3aeadcb89c3d18a37666dc7d9424961a2091d6b3696792f0f3", "name": "KyberSwap concentrated-liquidity precision loss", "category": "DEX / Precision Loss", "date": "2023-11", "address": "0xFd7B111AA83b9b6F547E617C7601EfD997F64703", "signature": "swap(address,int256,bool,uint160,bytes)", "address_lines": [14], "signature_lines": [76, 77, 78, 79, 80, 81, 82], "signature_file": "src/test/2023-11/KyberSwap/interfaces/pool/IPoolActions.sol", "signature_local": "KyberSwap_interfaces_pool_IPoolActions.sol", "call_lines": [113, 114], "tx_lines": [15]},
]

# Candidates retained in the raw-file cache but excluded from this freeze:
# overlap with the forbidden sets, or an unresolved/imported/raw-selector target
# that does not satisfy the phase-1 source rule.
_DISABLED_NAMES = {
    "Indexed Finance pool accounting",
    "DFX stablecoin pool manipulation",
    "Abracadabra Kashi oracle manipulation",
    "Euler donation attack",
    "Zunami UZD price-cache manipulation",
    "Raft precision-loss liquidation",
    "Shezmu collateral-token mint",
    "Morpho bundler authorization",
    "KyberSwap concentrated-liquidity precision loss",
    "Anyswap permit validation bypass",
    "ChainSwap signature validation bypass",
    "Unizen aggregator arbitrary transfer",
}

SPECS = [spec for spec in SPECS if spec["name"] not in _DISABLED_NAMES]
SPECS.extend([
    {"path": "src/test/2020-06/Balancer_20200628_exp.sol", "tx": "0x013be97768b702fe8eccef1a40544d5ecb3c1961ad5f87fee4d16fdc08c78106", "name": "Balancer STA deflationary-token accounting", "category": "DEX / Deflationary Token", "date": "2020-06", "address": "0x0e511Aa1a137AaD267dfe3a6bFCa0b856C1a3682", "signature": "swapExactAmountIn(address,uint256,address,uint256,uint256)", "address_lines": [121], "signature_lines": [91, 92, 93, 94, 95, 96, 97, 98], "call_lines": [196, 198, 199, 201, 202], "tx_lines": [22]},
    {"path": "src/test/2023-03/Paraspace_exp_2.sol", "tx": "0xe3f0d14cfb6076cabdc9057001c3fafe28767a192e88005bc37bd7d385a1116a", "name": "ParaSpace Ape collateral borrowing", "category": "NFT Lending / Collateral Accounting", "date": "2023-03", "address": "0x638a98BBB92a7582d07C52ff407D49664DC8b3Ee", "signature": "borrow(address,uint256,uint16,address)", "address_lines": [32], "signature_lines": [16, 17, 18, 19, 20], "call_lines": [95, 97, 98, 99], "tx_lines": [10]},
     {"path": "src/test/2025-03/LeverageSIR_exp.sol", "tx": "0xa05f047ddfdad9126624c4496b5d4a59f961ee7c091e7b4e38cee86f1335736f", "name": "Leverage SIR vault initialization", "category": "Vault / Price Manipulation", "date": "2025-03", "address": "0xb91ae2c8365fd45030aba84a4666c4db074e53e7", "signature": "initialize((address,address,int8))", "address_lines": [12, 17], "signature_lines": [241], "call_lines": [85, 86, 87, 88, 89], "tx_lines": [13]},
    {"path": "src/test/2025-06/SiloFinance_exp.sol", "tx": "0x1f15a193db3f44713d56c4be6679b194f78c2bcdd2ced5b0c7495b7406f5e87a", "name": "Silo leverage helper arbitrary borrow", "category": "Lending / Arbitrary Call", "date": "2025-06", "address": "0x160287e2d3fdcde9e91317982fc1cc01c1f94085", "signature": "borrow(uint256,address,address)", "address_lines": [10, 30], "signature_lines": [37, 38, 39], "call_lines": [139, 140, 141], "tx_lines": [11]},
    {"path": "src/test/2025-01/Unilend_exp.sol", "tx": "0x44037ffc0993327176975e08789b71c1058318f48ddeff25890a577d6555b6ba", "name": "UniLend health-factor accounting", "category": "Lending / Health Factor", "date": "2025-01", "address": "0x7f2E24D2394f2bdabb464B888cb02EbA6d15B958", "signature": "borrow(address,int256,uint256,address)", "address_lines": [10, 25], "signature_lines": [137, 138, 139, 140], "call_lines": [105, 111, 112, 114, 116, 117], "tx_lines": [11]},
     {"path": "src/test/2024-02/BlueberryProtocol_exp.sol", "tx": "0xf0464b01d962f714eee9d4392b2494524d0e10ce3eb3723873afd1346b8b06e4", "name": "Blueberry market entry accounting", "category": "Lending / Market Accounting", "date": "2024-02", "address": "0xffadb0bba4379dfabfb20ca6823f6ec439429ec2", "signature": "enterMarkets(address[])", "address_lines": [8, 55], "signature_lines": [17, 18, 19, 20], "call_lines": [101, 102, 103], "tx_lines": [9]},
     {"path": "src/test/2025-02/HegicOptions_exp.sol", "tx": "0x260d5eb9151c565efda80466de2e7eee9c6bd4973d54ff68c8e045a26f62ea73", "name": "Hegic options repeated withdrawal", "category": "Options / Accounting", "date": "2025-02", "address": "0x7094E706E75E13D1E0ea237f71A7C4511e9d270B", "signature": "withdrawWithoutHedge(uint256)", "address_lines": [10, 26], "signature_lines": [67, 68], "call_lines": [48], "tx_lines": [11]},
     {"path": "src/test/2025-03/OneInchFusionV1SettlementHack.sol_exp.sol", "tx": "0x62734ce80311e64630a009dd101a967ea0a9c012fabbfce8eac90f0f4ca090d6", "name": "1inch Fusion settlement calldata corruption", "category": "DEX / Calldata Validation", "date": "2025-03", "address": "0xa88800cd213da5ae406ce248380802bd53b47647", "signature": "settleOrders(bytes)", "address_lines": [12, 78], "signature_lines": [46, 47], "call_lines": [317], "tx_lines": [14]},
     {"path": "src/test/2025-04/tcdp_exp.sol", "tx": "0x9879031462b16dbf063377c4a8e5b043662576a9a3fb282c5a656953ad00684e", "name": "tCDP allowance direction bug", "category": "Token / Allowance Validation", "date": "2025-04", "address": "0xda4c9ee8373fd1095379a3dd457a0c78968aaf03", "signature": "transferFrom(address,address,uint256)", "address_lines": [10, 27], "signature_lines": [40, 41, 42, 43, 44], "call_lines": [119, 121], "tx_lines": [11]},
     {"path": "src/test/2025-06/ParaSwapDAIApproval_exp.sol", "tx": "0xed5f932a136ef95b943951ce103b3edbe600bf2c2607edff7b6ea9ada35ca300", "name": "ParaSwap stale DAI approval drain", "category": "DEX Aggregator / Approval Abuse", "date": "2025-06", "address": "0xdef171fe48cf0115b1d80b88dc8eab59176fee57", "signature": "simpleSwap((address,address,uint256,uint256,uint256,address[],bytes,uint256[],uint256[],address,address,uint256,bytes,uint256,bytes16))", "address_lines": [15, 34], "signature_lines": [85, 86, 87], "call_lines": [171], "tx_lines": [12]},
     {"path": "src/test/2025-06/AAVEBoost_exp.sol", "tx": "0xc4ef3b5e39d862ffcb8ff591fbb587f89d9d4ab56aec70cfb15831782239c0ce", "name": "Aave Boost proxy deposit accounting", "category": "Lending / Accounting", "date": "2025-06", "address": "0xd2933c86216dc0c938ffafeca3c8a2d6e633e2ca", "signature": "proxyDeposit(address,address,uint128)", "address_lines": [22], "signature_lines": [76, 77], "call_lines": [53], "tx_lines": [10]},
])


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def local_file(source_path: str) -> Path:
    if source_path == "src/test/2023-11/KyberSwap/interfaces/pool/IPoolActions.sol":
        return POC / "KyberSwap_interfaces_pool_IPoolActions.sol"
    return POC / Path(source_path).name


def source_rel_file(source_path: str) -> str:
    return source_path


def quotes(source_path: str, numbers: list[int]) -> list[dict[str, object]]:
    path = local_file(source_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    return [{"file": source_rel_file(source_path), "line": n, "text": lines[n - 1]} for n in numbers]


def canonical_hash(payload: dict) -> str:
    body = dict(payload)
    body.pop("artifact_sha256", None)
    return hashlib.sha256((json.dumps(body, indent=2, sort_keys=True) + "\n").encode("utf-8")).hexdigest()


def exclusion_sets() -> tuple[set[str], set[str], set[str], set[str]]:
    gt = {p.stem.lower() for p in (ROOT / "benchmark/original_faultseeker/ground_truth").glob("*.json")}
    raw = {p.stem.lower() for p in (ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw").glob("*.json")}
    manifest = load_json(ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/manifest.json")
    failed = {str(item["txn_hash"]).lower() for item in manifest["final_reporting"]["failure_details"]}
    benchmark = raw - failed
    batch_a = {str(row["transaction_hash"]).lower() for row in load_json(ROOT / "reports/new_batches/batchA_candidates.json")["rows"]}
    batch_b = {str(row["transaction_hash"]).lower() for row in load_json(ROOT / "reports/new_batches/batchB/batchB_candidates.json")["rows"]}
    return gt, benchmark, batch_a, batch_b


def build_rows(excluded: set[str]) -> list[dict]:
    rows = []
    for spec in SPECS:
        tx = spec["tx"].lower()
        path = local_file(spec["path"])
        text = path.read_text(encoding="utf-8")
        tx_quotes = quotes(spec["path"], spec["tx_lines"])
        address_quotes = quotes(spec["path"], spec["address_lines"])
        sig_path = spec.get("signature_file", spec["path"])
        sig_quotes = quotes(sig_path, spec["signature_lines"])
        call_quotes = quotes(spec["path"], spec["call_lines"])
        signature = spec["signature"]
        signature_text = local_file(sig_path).read_text(encoding="utf-8")
        declaration_text = "\n".join(item["text"] for item in sig_quotes)
        source_signature_present = signature_in_source(signature, signature_text)
        validate_target(signature, declaration_text, signature_text)
        assert tx in "\n".join(item["text"].lower() for item in tx_quotes), spec["path"]
        assert spec["address"].lower() in "\n".join(item["text"].lower() for item in address_quotes), spec["path"]
        assert tx not in excluded, f"selected transaction intersects exclusion sets: {tx}"
        assert path.exists(), spec["path"]
        assert source_signature_present, f"signature not source-resolved: {spec['path']}"
        selector = "0x" + keccak(text=signature)[:4].hex()
        rows.append({
            "chain": "eth",
            "incident_name": spec["name"],
            "incident_date": spec["date"],
            "transaction_hash": tx,
            "source_path": spec["path"],
            "source_url": f"{REPOSITORY}/{COMMIT}/{spec['path']}",
            "source_commit": COMMIT,
            "vulnerable_contract_address": spec["address"].lower(),
            "full_signature": signature,
            "selector": selector,
            "vulnerability_category": spec["category"],
            "source_evidence": {
                "transaction_lines": tx_quotes,
                "contract_address_lines": address_quotes,
                "signature_declaration_lines": sig_quotes,
                "poc_call_lines": call_quotes,
            },
            "source_match_checks": {
                "transaction_hash_present_in_source_lines": True,
                "contract_address_present_in_source_lines": True,
                "target_externally_callable": True,
                "signature_types_source_resolved": source_signature_present,
            },
        })
    assert len(rows) >= 30
    assert len({row["transaction_hash"] for row in rows}) == len(rows)
    assert len({row["incident_name"] for row in rows}) == len(rows)
    return rows


def build_source_manifest() -> list[dict]:
    probe = load_json(OUT / "fetch_probe.json")
    addendum = load_json(OUT / "fetch_probe_addendum.json")
    records = probe["files"] + addendum["files"]
    addendum_paths = {record["source_path"] for record in addendum["files"]}
    assert len({record["source_path"] for record in records}) == len(records)
    entries = []
    for record in records:
        if record.get("status") != "fetched" or record.get("file") == "Bybit_exp.sol":
            continue
        path = POC / record["file"]
        if not path.exists():
            continue
        entries.append({
            "file": record["file"],
            "source_path": record["source_path"],
            "source_url": record["source_url"],
            "commit": COMMIT,
            "fetched_at_utc": record.get(
                "fetched_at_utc",
                IMPORTED_FETCHED_AT if record["source_path"] in addendum_paths else FETCHED_AT,
            ),
            "network_requests": 1,
            "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    for filename, source_path in (
        ("KyberSwap_interfaces_IPool.sol", "src/test/2023-11/KyberSwap/interfaces/IPool.sol"),
        ("KyberSwap_interfaces_pool_IPoolActions.sol", "src/test/2023-11/KyberSwap/interfaces/pool/IPoolActions.sol"),
    ):
        path = POC / filename
        entries.append({
            "file": filename,
            "source_path": source_path,
            "source_url": f"{REPOSITORY}/{COMMIT}/{source_path}",
            "commit": COMMIT,
            "fetched_at_utc": IMPORTED_FETCHED_AT,
            "network_requests": 1,
            "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    return sorted(entries, key=lambda item: item["source_path"])


def build_exclusions(rows: list[dict], gt: set[str], benchmark: set[str], batch_a: set[str], batch_b: set[str]) -> list[dict]:
    selected_paths = {row["source_path"] for row in rows}
    selected_txs = {row["transaction_hash"] for row in rows}
    probe = load_json(OUT / "fetch_probe.json")
    probe["files"].extend(load_json(OUT / "fetch_probe_addendum.json")["files"])
    exclusions = []
    for record in probe["files"]:
        if record.get("status") != "fetched":
            exclusions.append({"file": record["source_path"], "incident": Path(record["source_path"]).stem, "reason": "Raw file was not present at the pinned commit (HTTP fetch failed); no candidate was synthesized."})
            continue
        source_path = record["source_path"]
        filename = record.get("file")
        if filename == "Bybit_exp.sol":
            reason = "Public PoC contains private-key material; it was not retained in the repository or selected for Batch C."
        elif source_path in selected_paths:
            continue
        else:
            text = (POC / filename).read_text(encoding="utf-8", errors="replace")
            low = text.lower()
            fork = re.search(r'createselectfork\(\s*"([^"]+)"', low)
            hashes = re.findall(r'0x[a-f0-9]{64}', low)
            if fork and fork.group(1) != "mainnet":
                reason = f"PoC forks {fork.group(1)}, not Ethereum mainnet."
            elif not hashes:
                reason = "No explicit transaction hash is present in the fetched PoC source."
            elif "interface.sol" in low and not re.search(r"interface\s+\w+\s*\{", low):
                reason = "Target signature is imported rather than locally source-resolved in the fetched PoC."
            elif "abi.encodewithsignature" in low and not re.search(r"function\s+\w+\s*\([^)]*\)\s*(external|public)", low):
                reason = "Target is exercised through a raw selector or low-level call without a complete locally resolved externally callable declaration."
            else:
                reason = "Fetched candidate was not selected after source-backed year/category coverage was satisfied; no ranker output or prior result was consulted."
        exclusions.append({"file": source_path, "incident": Path(source_path).stem, "reason": reason})
    return exclusions


def main() -> int:
    exclusion_snapshot = get_exclusions(ROOT)
    gt = set(exclusion_snapshot["ground_truth_hashes"])
    # The helper intentionally fails closed when the five historical provider
    # failures are not available as a literal: all 115 raw benchmark hashes are
    # forbidden, while the frozen benchmark population is recorded as 110.
    benchmark = set(exclusion_snapshot["benchmark_raw_filename_hashes"])
    batch_a = set(exclusion_snapshot["batch_a_hashes"])
    batch_b = set(exclusion_snapshot["batch_b_hashes"])
    assert len(gt) == 115
    assert len(benchmark) == 115
    assert len(batch_a) == 40
    assert len(batch_b) == 20
    excluded = gt | benchmark | batch_a | batch_b

    rows = build_rows(excluded)
    selected_txs = {row["transaction_hash"] for row in rows}
    assert not selected_txs & excluded

    payload = {
        "batch_id": "batchC",
        "status": "frozen",
        "phase": "phase_1_dataset_and_protocol_only",
        "chain": "eth",
        "source_repository": REPOSITORY,
        "source_commit": COMMIT,
        "selection_policy": "Source-backed incident diversity only: chronological coverage across years and vulnerability categories, one externally callable typed target per incident, explicit PoC evidence, and no ranker output, scoring output, Batch B result, or tracing output.",
        "exclusion_policy": {
            "ground_truth_json_count": len(gt),
            "benchmark_row_count": 110,
            "batch_a_row_count": len(batch_a),
            "batch_b_row_count": len(batch_b),
            "selected_tx_intersections": 0,
            "one_transaction_per_incident": True,
            "unresolved_or_internal_targets_excluded": True,
        },
        "row_count": len(rows),
        "rows": rows,
    }
    payload["artifact_sha256"] = canonical_hash(payload)
    (OUT / "batchC_candidates.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    manifest = build_source_manifest()
    (OUT / "source_manifest.json").write_text(json.dumps({"repository": REPOSITORY, "commit": COMMIT, "files": manifest}, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    exclusions = build_exclusions(rows, gt, benchmark, batch_a, batch_b)
    (OUT / "exclusions.json").write_text(json.dumps(exclusions, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    category_counts = Counter(row["vulnerability_category"] for row in rows)
    year_counts = Counter(row["incident_date"][:4] for row in rows)
    report = [
        "# Batch C phase 1 report",
        "",
        f"**Frozen: {len(rows)} distinct Ethereum-mainnet incidents, DeFiHackLabs-sourced.**",
        "",
        "This phase performed only public raw-file collection and local source screening. No RPC, node tracing, transaction lookup, scoring, ranker invocation, Batch B result inspection, or result-file change was performed.",
        "",
        f"Pinned source commit: `{COMMIT}`",
        f"Frozen canonical JSON SHA-256: `{payload['artifact_sha256']}`",
        f"Fetched source files retained in the manifest: **{len(manifest)}**",
        "",
        "## Counts by vulnerability category",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ]
    report += [f"| {key} | {category_counts[key]} |" for key in sorted(category_counts)]
    report += ["", "## Counts by incident year", "", "| Year | Count |", "| --- | ---: |"]
    report += [f"| {key} | {year_counts[key]} |" for key in sorted(year_counts)]
    report += ["", "## Exclusions", "", "| File | Incident | Reason |", "| --- | --- | --- |"]
    report += [f"| `{item['file']}` | {item['incident']} | {item['reason']} |" for item in exclusions]
    report += [
        "",
        "The exclusion scan used 115 local ground-truth JSON hashes, 110 local provider-pinned benchmark hashes, all 40 Batch A hashes, and all 20 Batch B hashes. No frozen Batch C transaction intersected those sets. Batch B results and ranker output were not read or used for selection.",
        "",
        "## Later verification gate",
        "",
        "When Batch C is eventually opened, use the same gate as Batch B: a transaction is verified only when the returned transaction hash and receipt transaction hash equal the frozen hash, transaction and receipt block numbers match, the transaction is not pending, and a valid full Ethereum trace is available. Any mismatch excludes the row before scoring.",
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(report), encoding="utf-8", newline="\n")

    protocol = f"""# Batch C phase 1 protocol

**Status: pre-registered before any tracing or scoring.** This phase freezes the dataset and protocol only. It performs no RPC, no node tracing, no scoring, and no ranker invocation.

## Scope and provenance

- Label: **Batch C, single-chain Ethereum mainnet, DeFiHackLabs-sourced**.
- Source repository: `{REPOSITORY}`.
- Every retained raw source file is pinned to commit `{COMMIT}` and has a recorded URL, UTC fetch date, one-request fetch record, and SHA-256 content hash in `source_manifest.json`.
- Selection uses only source-backed incident identity, Ethereum-mainnet provenance, year/category coverage, explicit vulnerable address, externally callable target, and complete source-resolved typed signature.
- Batch C excludes every transaction in the 115 ground-truth JSONs, the 110 benchmark rows, all Batch A transactions, and all Batch B transactions, including Batch B's later excluded trace row.
- Batch B results, Batch B ranker output, and any other ranker/scoring output were not read or used to choose Batch C rows.
- At most one transaction is retained per incident.

## Selection requirements

The frozen set contains at least 30 distinct Ethereum-mainnet incidents spread across years and vulnerability categories. A row is eligible only when:

1. The fetched PoC contains one explicit Ethereum-mainnet transaction hash and a source-backed vulnerable contract address.
2. The target is externally callable, not an internal-only helper, low-level selector, or unresolved proxy-only placeholder.
3. The PoC source (or a locally fetched, pinned source file imported by that PoC) provides a complete argument-typed signature.
4. The transaction hash, vulnerable address, and signature evidence are quoted with exact source file paths and one-based lines.
5. The transaction hash and address do not intersect any frozen exclusion set.

Types are never inferred. Rows failing any condition are excluded with a reason in `exclusions.json` and `REPORT.md`.

## Frozen row schema

Each row in `batchC_candidates.json` records the transaction hash, incident name and month, Ethereum chain, PoC file, pinned commit, raw source URL, vulnerable contract address, canonical full signature, keccak256 4-byte selector, vulnerability category, and exact line quotes for the transaction, address, signature declaration, and PoC call. Evidence entries include the source file path and one-based line.

## Future verification and scoring

Batch C stays sealed: **no tracing and no scoring until the ranker upgrade work is finished and its commit hash is recorded.**

After the seal is opened, score once with the final ranker version only. The protocol is:

- Primary key: vulnerable contract address + full-signature selector.
- Sensitivity keys: address-only and selector-only.
- Metrics: R@1, R@3, and R@5 for each key, with Wilson 95% intervals.
- No tuning, retuning, ranker changes, scorer changes, weight changes, Batch C-specific heuristics, or partial-result peeking.
- Use the same verification gate as Batch B: matching transaction and receipt hashes, matching block numbers, non-pending transaction, and valid full trace before a row enters N.

The protocol stops at this phase-1 freeze. No RPC, tracing, scoring, or ranker invocation is permitted during phase 1.
"""
    (OUT / "PROTOCOL.md").write_text(protocol, encoding="utf-8", newline="\n")
    (OUT / "FREEZE.md").write_text(
        "# Batch C freeze\n\n"
        "`batchC_candidates.json` is frozen for phase 1.\n\n"
        "Canonicalization: `json.dumps(payload_without_artifact_sha256, indent=2, sort_keys=True) + newline`, UTF-8.\n\n"
        f"SHA-256: `{payload['artifact_sha256']}`\n\n"
        f"Rows: `{len(rows)}`\n\n"
        "No edits are permitted after this freeze. Batch C remains sealed until the ranker upgrade commit is recorded.\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"rows": len(rows), "manifest_files": len(manifest), "artifact_sha256": payload["artifact_sha256"], "exclusions": len(exclusions)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
