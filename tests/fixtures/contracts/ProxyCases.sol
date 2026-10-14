// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract StorageProxy {
    address public implementation;
    uint256 public value;

    function setImplementation(address target) external { implementation = target; }

    fallback() external payable {
        address target = implementation;
        require(target != address(0), "missing implementation");
        assembly {
            calldatacopy(0, 0, calldatasize())
            let ok := delegatecall(gas(), target, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch ok
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
}

contract ProxyImplementation {
    address private reserved;
    uint256 public value;

    function setValue(uint256 nextValue) external { value = nextValue; }
}
