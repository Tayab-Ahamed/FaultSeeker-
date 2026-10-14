// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract GuardedVault {
    mapping(address => uint256) public balances;
    uint256 private status = 1;

    function deposit() external payable { balances[msg.sender] += msg.value; }

    function withdraw() external {
        require(status == 1, "reentrant");
        status = 2;
        uint256 amount = balances[msg.sender];
        require(amount > 0, "empty");
        balances[msg.sender] = 0;
        (bool sent,) = msg.sender.call{value: amount}("");
        require(sent, "send failed");
        status = 1;
    }
}

contract GuardProbe {
    GuardedVault public vault;
    bool public nestedRejected;

    function setVault(address target) external { vault = GuardedVault(target); }

    function attack() external payable {
        vault.deposit{value: msg.value}();
        vault.withdraw();
    }

    receive() external payable {
        (bool ok,) = address(vault).call(abi.encodeWithSignature("withdraw()"));
        nestedRejected = !ok;
    }
}
