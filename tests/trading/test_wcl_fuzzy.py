#!/usr/bin/env python

from ethereum import tester
from pytest import fixture
from random import randint, random as randfloat
from utils import bytesToLong, fix

# binary outcomes
YES = 1
NO = 0

# order types
BID = 1
ASK = 2

# order fields
ATTOSHARES = 0
DISPLAY_PRICE = 1
OWNER = 2
OUTCOME = 3
TOKENS_ESCROWED = 4
SHARES_ESCROWED = 5
BETTER_ORDER_ID = 6
WORSE_ORDER_ID = 7
GAS_PRICE = 8

# TODO: turn these into 24 parameterized tests rather than 3 tests that each execute 8 sub-tests

def execute(contractsFixture, market, orderType, orderSize, orderPrice, orderOutcome, makerLongShares, makerShortShares, makerTokens, takerLongShares, takerShortShares, takerTokens, expectedMakerLongShares, expectedMakerShortShares, expectedMakerTokens, expectedTakerLongShares, expectedTakerShortShares, expectedTakerTokens):
    contractsFixture.resetSnapshot()

    def acquireLongShares(outcome, amount, approvalAddress, sender):
        if amount == 0: return

        cash = contractsFixture.cash
        shareToken = contractsFixture.applySignature('shareToken', market.getShareToken(outcome))
        completeSets = contractsFixture.contracts['completeSets']
        makeOrder = contractsFixture.contracts['makeOrder']
        takeOrder = contractsFixture.contracts['takeOrder']

        cashRequired = amount * market.getCompleteSetCostInAttotokens() / 10**18
        assert cash.publicDepositEther(value=cashRequired, sender = sender)
        assert cash.approve(completeSets.address, cashRequired, sender = sender)
        assert completeSets.publicBuyCompleteSets(market.address, amount, sender = sender)
        assert shareToken.approve(approvalAddress, amount, sender = sender)
        for otherOutcome in range(0, market.getNumberOfOutcomes()):
            if otherOutcome == outcome: continue
            otherShareToken = contractsFixture.applySignature('shareToken', market.getShareToken(otherOutcome))
            assert otherShareToken.transfer(0, amount, sender = sender)

    def acquireShortShareSet(outcome, amount, approvalAddress, sender):
        if amount == 0: return

        cash = contractsFixture.cash
        shareToken = contractsFixture.applySignature('shareToken', market.getShareToken(outcome))
        completeSets = contractsFixture.contracts['completeSets']
        makeOrder = contractsFixture.contracts['makeOrder']
        takeOrder = contractsFixture.contracts['takeOrder']

        cashRequired = amount * market.getCompleteSetCostInAttotokens() / 10**18
        assert cash.publicDepositEther(value=cashRequired, sender = sender)
        assert cash.approve(completeSets.address, cashRequired, sender = sender)
        assert completeSets.publicBuyCompleteSets(market.address, amount, sender = sender)
        assert shareToken.transfer(0, amount, sender = sender)
        for otherOutcome in range(0, market.getNumberOfOutcomes()):
            if otherOutcome == outcome: continue
            otherShareToken = contractsFixture.applySignature('shareToken', market.getShareToken(otherOutcome))
            assert otherShareToken.approve(approvalAddress, amount, sender = sender)

    def acquireTokens(amount, approvalAddress, sender):
        if amount == 0: return

        cash = contractsFixture.cash
        makeOrder = contractsFixture.contracts['makeOrder']
        takeOrder = contractsFixture.contracts['takeOrder']

        assert cash.publicDepositEther(value = amount, sender = sender)
        assert cash.approve(approvalAddress, amount, sender = sender)

    cash = contractsFixture.cash
    orders = contractsFixture.contracts['orders']
    makeOrder = contractsFixture.contracts['makeOrder']
    takeOrder = contractsFixture.contracts['takeOrder']
    completeSets = contractsFixture.contracts['completeSets']

    makerAddress = tester.a1
    takerAddress = tester.a2
    makerKey = tester.k1
    takerKey = tester.k2

    # make order
    acquireLongShares(orderOutcome, makerLongShares, makeOrder.address, sender = makerKey)
    acquireShortShareSet(orderOutcome, makerShortShares, makeOrder.address, sender = makerKey)
    acquireTokens(makerTokens, makeOrder.address, sender = makerKey)
    orderId = makeOrder.publicMakeOrder(orderType, orderSize, orderPrice, market.address, orderOutcome, 0, 0, 42, sender = makerKey)

    # validate the order
    order = orders.getOrder(orderId, orderType, market.address, orderOutcome)
    assert order[ATTOSHARES] == orderSize
    assert order[DISPLAY_PRICE] == orderPrice
    assert order[OWNER] == bytesToLong(makerAddress)
    assert order[OUTCOME] == orderOutcome
    assert order[TOKENS_ESCROWED] == makerTokens
    assert order[SHARES_ESCROWED] == makerLongShares or makerShortShares

    # take order
    acquireLongShares(orderOutcome, takerLongShares, takeOrder.address, sender = takerKey)
    acquireShortShareSet(orderOutcome, takerShortShares, takeOrder.address, sender = takerKey)
    acquireTokens(takerTokens, takeOrder.address, sender = takerKey)
    remaining = takeOrder.publicTakeOrder(orderId, orderType, market.address, orderOutcome, orderSize, sender = takerKey)
    assert not remaining

    # assert final state
    assert cash.balanceOf(makerAddress) == expectedMakerTokens
    assert cash.balanceOf(takerAddress) == expectedTakerTokens
    for outcome in range(0, market.getNumberOfOutcomes()):
        shareToken = contractsFixture.applySignature('shareToken', market.getShareToken(outcome))
        if outcome == orderOutcome:
            assert shareToken.balanceOf(makerAddress) == expectedMakerLongShares
            assert shareToken.balanceOf(takerAddress) == expectedTakerLongShares
        else:
            assert shareToken.balanceOf(makerAddress) == expectedMakerShortShares
            assert shareToken.balanceOf(takerAddress) == expectedTakerShortShares

def execute_bidOrder_tests(contractsFixture, market, fxpAmount, fxpPrice):
    longCost = long(fxpAmount * (fxpPrice - market.getMinDisplayPrice()) / 10**18)
    shortCost = long(fxpAmount * (market.getMaxDisplayPrice() - fxpPrice) / 10**18)
    completeSetFees = long(fxpAmount * market.getCompleteSetCostInAttotokens() * fix(0.0101) / 10**18 / 10**18)

    # maker escrows cash, taker pays with cash
    execute(
        contractsFixture = contractsFixture,
        market = market,
        orderType = BID,
        orderSize = fxpAmount,
        orderPrice = fxpPrice,
        orderOutcome = YES,
        makerLongShares = 0,
        makerShortShares = 0,
        makerTokens = longCost,
        takerLongShares = 0,
        takerShortShares = 0,
        takerTokens = shortCost,
        expectedMakerLongShares = fxpAmount,
        expectedMakerShortShares = 0,
        expectedMakerTokens = 0,
        expectedTakerLongShares = 0,
        expectedTakerShortShares = fxpAmount,
        expectedTakerTokens = 0)

    # maker escrows shares, taker pays with shares
    execute(
        contractsFixture = contractsFixture,
        market = market,
        orderType = BID,
        orderSize = fxpAmount,
        orderPrice = fxpPrice,
        orderOutcome = YES,
        makerLongShares = 0,
        makerShortShares = fxpAmount,
        makerTokens = 0,
        takerLongShares = fxpAmount,
        takerShortShares = 0,
        takerTokens = 0,
        expectedMakerLongShares = 0,
        expectedMakerShortShares = 0,
        expectedMakerTokens = shortCost,
        expectedTakerLongShares = 0,
        expectedTakerShortShares = 0,
        expectedTakerTokens = longCost - completeSetFees)

    # maker escrows cash, taker pays with shares
    execute(
        contractsFixture = contractsFixture,
        market = market,
        orderType = BID,
        orderSize = fxpAmount,
        orderPrice = fxpPrice,
        orderOutcome = YES,
        makerLongShares = 0,
        makerShortShares = 0,
        makerTokens = longCost,
        takerLongShares = fxpAmount,
        takerShortShares = 0,
        takerTokens = 0,
        expectedMakerLongShares = fxpAmount,
        expectedMakerShortShares = 0,
        expectedMakerTokens = 0,
        expectedTakerLongShares = 0,
        expectedTakerShortShares = 0,
        expectedTakerTokens = longCost)

    # maker escrows shares, taker pays with cash
    execute(
        contractsFixture = contractsFixture,
        market = market,
        orderType = BID,
        orderSize = fxpAmount,
        orderPrice = fxpPrice,
        orderOutcome = YES,
        makerLongShares = 0,
        makerShortShares = fxpAmount,
        makerTokens = 0,
        takerLongShares = 0,
        takerShortShares = 0,
        takerTokens = shortCost,
        expectedMakerLongShares = 0,
        expectedMakerShortShares = 0,
        expectedMakerTokens = shortCost,
        expectedTakerLongShares = 0,
        expectedTakerShortShares = fxpAmount,
        expectedTakerTokens = 0)

def execute_askOrder_tests(contractsFixture, market, fxpAmount, fxpPrice):
    longCost = long(fxpAmount * (fxpPrice - market.getMinDisplayPrice()) / 10**18)
    shortCost = long(fxpAmount * (market.getMaxDisplayPrice() - fxpPrice) / 10**18)
    completeSetFees = long(fxpAmount * market.getCompleteSetCostInAttotokens() * fix(0.0101) / 10**18 / 10**18)

    # maker escrows cash, taker pays with cash
    execute(
        contractsFixture = contractsFixture,
        market = market,
        orderType = ASK,
        orderSize = fxpAmount,
        orderPrice = fxpPrice,
        orderOutcome = YES,
        makerLongShares = 0,
        makerShortShares = 0,
        makerTokens = shortCost,
        takerLongShares = 0,
        takerShortShares = 0,
        takerTokens = longCost,
        expectedMakerLongShares = 0,
        expectedMakerShortShares = fxpAmount,
        expectedMakerTokens = 0,
        expectedTakerLongShares = fxpAmount,
        expectedTakerShortShares = 0,
        expectedTakerTokens = 0)

    # maker escrows shares, taker pays with shares
    execute(
        contractsFixture = contractsFixture,
        market = market,
        orderType = ASK,
        orderSize = fxpAmount,
        orderPrice = fxpPrice,
        orderOutcome = YES,
        makerLongShares = fxpAmount,
        makerShortShares = 0,
        makerTokens = 0,
        takerLongShares = 0,
        takerShortShares = fxpAmount,
        takerTokens = 0,
        expectedMakerLongShares = 0,
        expectedMakerShortShares = 0,
        expectedMakerTokens = longCost,
        expectedTakerLongShares = 0,
        expectedTakerShortShares = 0,
        expectedTakerTokens = shortCost - completeSetFees)

    # maker escrows cash, taker pays with shares
    execute(
        contractsFixture = contractsFixture,
        market = market,
        orderType = ASK,
        orderSize = fxpAmount,
        orderPrice = fxpPrice,
        orderOutcome = YES,
        makerLongShares = 0,
        makerShortShares = 0,
        makerTokens = shortCost,
        takerLongShares = 0,
        takerShortShares = fxpAmount,
        takerTokens = 0,
        expectedMakerLongShares = 0,
        expectedMakerShortShares = fxpAmount,
        expectedMakerTokens = 0,
        expectedTakerLongShares = 0,
        expectedTakerShortShares = 0,
        expectedTakerTokens = shortCost)

    # maker escrows shares, taker pays with cash
    execute(
        contractsFixture = contractsFixture,
        market = market,
        orderType = ASK,
        orderSize = fxpAmount,
        orderPrice = fxpPrice,
        orderOutcome = YES,
        makerLongShares = fxpAmount,
        makerShortShares = 0,
        makerTokens = 0,
        takerLongShares = 0,
        takerShortShares = 0,
        takerTokens = longCost,
        expectedMakerLongShares = 0,
        expectedMakerShortShares = 0,
        expectedMakerTokens = longCost,
        expectedTakerLongShares = fxpAmount,
        expectedTakerShortShares = 0,
        expectedTakerTokens = 0)

def test_binary(contractsFixture, randomAmount, randomNormalizedPrice):
    market = contractsFixture.binaryMarket
    print 'Random amount: ' + str(randomAmount)
    print 'Random price: ' + str(randomNormalizedPrice)
    fxpAmount = fix(randomAmount)
    fxpPrice = long(randomNormalizedPrice * market.getCompleteSetCostInAttotokens() + market.getMinDisplayPrice())
    print "Start Fuzzy WCL tests - Binary Market - bidOrders."
    print ""
    execute_bidOrder_tests(contractsFixture, market, fxpAmount, fxpPrice)
    print ""
    print "Finished Fuzzy WCL tests - Binary Market - bidOrders."
    print ""
    print "Start Fuzzy WCL tests - Binary Market - askOrders."
    print ""
    execute_askOrder_tests(contractsFixture, market, fxpAmount, fxpPrice)
    print ""
    print "Finished Fuzzy WCL tests - Binary Market - askOrders."
    print ""

def test_categorical(contractsFixture, randomAmount, randomNormalizedPrice):
    market = contractsFixture.categoricalMarket
    print 'Random amount: ' + str(randomAmount)
    print 'Random price: ' + str(randomNormalizedPrice)
    fxpAmount = fix(randomAmount)
    fxpPrice = long(randomNormalizedPrice * market.getCompleteSetCostInAttotokens() + market.getMinDisplayPrice())
    print "Start Fuzzy WCL tests - Categorical Market - bidOrders."
    print ""
    execute_bidOrder_tests(contractsFixture, market, fxpAmount, fxpPrice)
    print ""
    print "Finished Fuzzy WCL tests - Categorical Market - bidOrders."
    print ""
    print "Start Fuzzy WCL tests - Categorical Market - askOrders."
    print ""
    execute_askOrder_tests(contractsFixture, market, fxpAmount, fxpPrice)
    print ""
    print "Finished Fuzzy WCL tests - Categorical Market - askOrders."
    print ""

def test_scalar(contractsFixture, randomAmount, randomNormalizedPrice):
    market = contractsFixture.scalarMarket
    print 'Random amount: ' + str(randomAmount)
    print 'Random price: ' + str(randomNormalizedPrice)
    fxpAmount = fix(randomAmount)
    fxpPrice = long(randomNormalizedPrice * market.getCompleteSetCostInAttotokens() + market.getMinDisplayPrice())
    print "Start Fuzzy WCL tests - Scalar Market - bidOrders."
    print ""
    execute_bidOrder_tests(contractsFixture, market, fxpAmount, fxpPrice)
    print ""
    print "Finished Fuzzy WCL tests - Scalar Market - bidOrders."
    print ""
    print "Start Fuzzy WCL tests - Scalar Market - askOrders."
    print ""
    execute_askOrder_tests(contractsFixture, market, fxpAmount, fxpPrice)
    print ""
    print "Finished Fuzzy WCL tests - Scalar Market - askOrders."
    print ""

# check randomly generated numbers to make sure they aren't unreasonable
def check_randoms(market, price):
    fxpPrice = fix(price)
    fxpMinDisplayPrice = market.getMinDisplayPrice()
    fxpMaxDisplayPrice = market.getMaxDisplayPrice()
    fxpTradingFee = fix(0.0101)
    if fxpPrice <= fxpMinDisplayPrice:
        return 0
    if fxpPrice >= fxpMaxDisplayPrice:
        return 0
    if fxpTradingFee >= fxpPrice - fxpMinDisplayPrice:
        return 0
    if fxpTradingFee >= fxpMaxDisplayPrice - fxpPrice:
        return 0
    return 1

@fixture
def numberOfIterations():
    return 1

@fixture
def makerAddress():
    return tester.a1

@fixture
def takerAddress():
    return tester.a2

@fixture
def makerKey():
    return tester.k1

@fixture
def takerKey():
    return tester.k2

@fixture
def randomAmount():
    return randint(1, 11)

@fixture
def randomNormalizedPrice():
    price = 0
    while price < 0.0101 or price > 0.9899:
        price = randfloat()
    return price