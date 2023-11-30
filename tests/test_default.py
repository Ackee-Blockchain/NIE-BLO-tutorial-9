from wake.testing import *

from pytypes.contracts.CPAMM import CPAMM
from pytypes.contracts.CREATE3Factory import CREATE3Factory, TemporaryContract
from pytypes.contracts.ERC20 import ERC20
from pytypes.contracts.MaliciousERC20 import MaliciousERC20

# decimals
USDC_DECIMALS = 10**6
DOGE_DECIMALS = 10**18


def setup_amm(usdc_deployer: Account, doge_deployer: Account):
    factory = CREATE3Factory.deploy()
    factory.deployContract(keccak256(b"USDC"), ERC20.get_creation_code() + Abi.encode(["string", "string", "uint8"], ["USD Coin", "USDC", 6]), from_=usdc_deployer)
    factory.deployContract(keccak256(b"DOGE"), ERC20.get_creation_code() + Abi.encode(["string", "string", "uint8"], ["Dogecoin", "DOGE", 18]), from_=doge_deployer)

    usdc = ERC20(factory.getDeployed(usdc_deployer, keccak256(b"USDC")))
    doge = ERC20(factory.getDeployed(doge_deployer, keccak256(b"DOGE")))
    usdc.label = "USDC"
    doge.label = "DOGE"

    amm = CPAMM.deploy(usdc, doge)
    amm.label = "AMM"

    return usdc, doge, amm, factory


def print_token_balances(usdc: ERC20, doge: ERC20, address: Account):
    usdc_bal = usdc.balanceOf(address)
    doge_bal = doge.balanceOf(address)
    print(f"{address.label}: {usdc_bal} -> {usdc_bal / USDC_DECIMALS} USDC")
    print(f"{address.label}: {doge_bal} -> {doge_bal / DOGE_DECIMALS} DOGE")


def add_liquidity(usdc: ERC20, doge: ERC20, amm: CPAMM, usdc_amount: int, doge_amount: int, a: Account):
    usdc.approve(amm, usdc_amount * USDC_DECIMALS, from_=a)
    doge.approve(amm, doge_amount * DOGE_DECIMALS, from_=a)
    amm.addLiquidity(usdc_amount * USDC_DECIMALS, doge_amount * DOGE_DECIMALS, from_=a)


def revert_handler(e: TransactionRevertedError):
    if e.tx is not None:
        print(e.tx.call_trace)
        print(e.tx.console_logs)

@default_chain.connect()
@on_revert(revert_handler)
def test_default():
    # set accounts
    usdc_boss = default_chain.accounts[1]
    attacker = default_chain.accounts[2]
    victim = default_chain.accounts[3]
    attacker.label = "Attacker"
    victim.label = "Victim"

    # deploy contracts
    (usdc, doge, amm, factory) = setup_amm(usdc_boss, attacker)

    # some initial funding
    usdc.mint(victim, 10000 * USDC_DECIMALS)
    doge.mint(victim, 10000 * DOGE_DECIMALS)
    usdc.mint(attacker, 10000 * USDC_DECIMALS)
    doge.mint(attacker, 10000 * DOGE_DECIMALS)

    # someone adds liquidity to pool
    add_liquidity(usdc, doge, amm, 1000, 10000, victim)

    # attacker adds liquidity to pool
    add_liquidity(usdc, doge, amm, 100, 1000, attacker)

    assert usdc.balanceOf(victim) == 9000 * USDC_DECIMALS
    assert usdc.balanceOf(attacker) == 9900 * USDC_DECIMALS
    assert doge.balanceOf(victim) == 0 * DOGE_DECIMALS
    assert doge.balanceOf(attacker) == 9000 * DOGE_DECIMALS

    # perform swaps
    doge.approve(amm, 200 * DOGE_DECIMALS, from_=attacker)
    amm.swap(doge, 100 * DOGE_DECIMALS, from_=attacker)
    amm.swap(doge, 100 * DOGE_DECIMALS, from_=attacker)

    print_token_balances(usdc, doge, victim)
    print_token_balances(usdc, doge, attacker)


@default_chain.connect()
@on_revert(revert_handler)
def test_attack():
    print("=" * 30)
    print("Testing attack...")
    print("=" * 30)
    # set accounts
    usdc_boss = default_chain.accounts[1]
    attacker = default_chain.accounts[2]
    victim = default_chain.accounts[3]
    attacker.label = "Attacker"
    victim.label = "Victim"

    # deploy contracts
    (usdc, doge, amm, factory) = setup_amm(usdc_boss, attacker)

    # some initial funding
    usdc.mint(victim, 10000 * USDC_DECIMALS)
    doge.mint(victim, 10000 * DOGE_DECIMALS)
    usdc.mint(attacker, 10000 * USDC_DECIMALS)
    doge.mint(attacker, 10000 * DOGE_DECIMALS)

    # someone adds liquidity to pool
    add_liquidity(usdc, doge, amm, 1000, 10000, victim)

    # attacker adds liquidity to pool
    add_liquidity(usdc, doge, amm, 100, 1000, attacker)

    assert usdc.balanceOf(victim) == 9000 * USDC_DECIMALS
    assert usdc.balanceOf(attacker) == 9900 * USDC_DECIMALS
    assert doge.balanceOf(victim) == 0 * DOGE_DECIMALS
    assert doge.balanceOf(attacker) == 9000 * DOGE_DECIMALS

    # CREATE3 HACK
    # TODO: get more USDC from AMM than in previous test without
    #       adding lines of code that interacts with AMM
    #

    # perform swaps
    doge.approve(amm, 200 * DOGE_DECIMALS, from_=attacker)
    amm.swap(doge, 100 * DOGE_DECIMALS, from_=attacker)
    amm.swap(doge, 100 * DOGE_DECIMALS, from_=attacker)

    print_token_balances(usdc, doge, victim)
    print_token_balances(usdc, doge, attacker)