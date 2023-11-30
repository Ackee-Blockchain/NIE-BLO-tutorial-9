// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.20;

library Bytes32AddressLib {
    function fromLast20Bytes(bytes32 bytesValue) internal pure returns (address) {
        return address(uint160(uint256(bytesValue)));
    }

    function fillLast12Bytes(address addressValue) internal pure returns (bytes32) {
        return bytes32(bytes20(addressValue));
    }
}

library CREATE3 {
    using Bytes32AddressLib for bytes32;

    bytes internal constant TEMP_BYTECODE = type(TemporaryContract).creationCode;
    bytes32 internal constant TEMP_BYTECODE_HASH = keccak256(TEMP_BYTECODE);

    function deploy(
        bytes32 salt,
        bytes memory creationCode,
        uint256 value
    ) internal returns (address deployed) {
        bytes memory temp = TEMP_BYTECODE;
        address proxy;
        assembly {
            // Deploy a new contract with our pre-made bytecode via CREATE2.
            // We start 32 bytes into the code to avoid copying the byte length.
            proxy := create2(0, add(temp, 32), mload(temp), salt)
        }
        require(proxy != address(0), "DEPLOYMENT_FAILED");

        TemporaryContract(proxy).metamorph(creationCode);

        deployed = getDeployed(salt);
    }

    function getDeployed(bytes32 salt) internal view returns (address) {
        return getDeployed(salt, address(this));
    }

    function getDeployed(bytes32 salt, address creator) internal pure returns (address) {
        address proxy = keccak256(
            abi.encodePacked(
                // Prefix:
                bytes1(0xFF),
                // Creator:
                creator,
                // Salt:
                salt,
                // Bytecode hash:
                TEMP_BYTECODE_HASH
            )
        ).fromLast20Bytes();

        return
            keccak256(
                abi.encodePacked(
                    // 0xd6 = 0xc0 (short RLP prefix) + 0x16 (length of: 0x94 ++ proxy ++ 0x01)
                    // 0x94 = 0x80 + 0x14 (0x14 = the length of an address, 20 bytes, in hex)
                    hex"d6_94",
                    proxy,
                    hex"01" // Nonce of the proxy contract (1)
                )
            ).fromLast20Bytes();
    }
}

interface ICREATE3Factory {
    function deployContract(bytes32 salt, bytes memory creationCode)
        external
        payable
        returns (address deployed);

    function getDeployed(address deployer, bytes32 salt)
        external
        view
        returns (address deployed);
}

contract CREATE3Factory is ICREATE3Factory {
    function deployContract(bytes32 salt, bytes memory creationCode)
        external
        payable
        override
        returns (address deployed)
    {
        return CREATE3.deploy(salt, creationCode, msg.value);
    }

    function getDeployed(address deployer, bytes32 salt)
        external
        view
        override
        returns (address deployed)
    {
        return CREATE3.getDeployed(salt);
    }
}


contract TemporaryContract {
    function metamorph(bytes memory initCode) public payable {
        assembly {
            if iszero(create(0, add(initCode, 32), mload(initCode))) {
                revert(0, 0)
            }
            selfdestruct(caller())
        }
    }
}