#!/usr/bin/env python

from ContractsFixture import ContractsFixture
from ethereum import tester
from ethereum.tester import TransactionFailed
from iocapture import capture
from pytest import raises, fixture
from utils import parseCapturedLogs, bytesToLong, longToHexString, bytesToHexString, fix, unfix

tester.gas_limit = long(4.2 * 10**6)

YES = 1
NO = 0

BID = 1
ASK = 2

ATTOSHARES = 0
DISPLAY_PRICE = 1
OWNER = 2
OUTCOME = 3
TOKENS_ESCROWED = 4
SHARES_ESCROWED = 5
BETTER_ORDER_ID = 6
WORSE_ORDER_ID = 7
GAS_PRICE = 8

def test_initialize():
    fixture = ContractsFixture()
    makeOrder = fixture.uploadAndAddToController('../src/trading/makeOrder.se')

    makeOrder.initialize(tester.a0)

    assert makeOrder.setController(tester.a1)

def test_initialize_failure():
    fixture = ContractsFixture()
    makeOrder = fixture.uploadAndAddToController('../src/trading/makeOrder.se')

    with raises(TransactionFailed):
        makeOrder.initialize(tester.a0, sender = tester.k1)
    with raises(TransactionFailed):
        # NOTE: must be last since it changes contract state
        makeOrder.initialize(tester.a0)
        makeOrder.initialize(tester.a1)

def test_setController_failure():
    fixture = ContractsFixture()
    makeOrder = fixture.uploadAndAddToController('../src/trading/makeOrder.se')
    makeOrder.initialize(tester.a0)

    with raises(TransactionFailed):
        makeOrder.setController(tester.a1, sender = tester.k1)

def test_publicMakeOrder_bid():
    fixture = ContractsFixture()
    (_, cash, market, orders, makeOrder, _) = fixture.prepOrders()
    cash.publicDepositEther(value = 10**17)
    cash.approve(makeOrder.address, 10**17)

    orderId = makeOrder.publicMakeOrder(BID, 10**18, 10**17, market.address, 1, 0, 0, 7)
    assert orderId

    order = orders.getOrder(orderId, BID, market.address, 1)
    assert order[ATTOSHARES] == 10**18
    assert order[DISPLAY_PRICE] == 10**17
    assert order[OWNER] == bytesToLong(tester.a0)
    assert order[OUTCOME] == 1
    assert order[TOKENS_ESCROWED] == 10**17
    assert order[SHARES_ESCROWED] == 0
    assert order[BETTER_ORDER_ID] == 0
    assert order[WORSE_ORDER_ID] == 0
    assert order[GAS_PRICE] == 1

def test_publicMakeOrder_ask():
    fixture = ContractsFixture()
    (_, cash, market, orders, makeOrder, _) = fixture.prepOrders()
    cash.publicDepositEther(value = 10**18)
    cash.approve(makeOrder.address, 10**18)

    orderId = makeOrder.publicMakeOrder(ASK, 10**18, 10**17, market.address, 0, 0, 0, 7)

    order = orders.getOrder(orderId, ASK, market.address, 0)
    assert order[ATTOSHARES] == 10**18
    assert order[DISPLAY_PRICE] == 10**17
    assert order[OWNER] == bytesToLong(tester.a0)
    assert order[OUTCOME] == 0
    assert order[TOKENS_ESCROWED] == 10**18 - 10**17
    assert order[SHARES_ESCROWED] == 0
    assert order[BETTER_ORDER_ID] == 0
    assert order[WORSE_ORDER_ID] == 0
    assert order[GAS_PRICE] == 1
    assert cash.balanceOf(market.address) == 10**18 - 10**17

def test_publicMakeOrder_bid2():
    fixture = ContractsFixture()
    (_, cash, market, orders, makeOrder, _) = fixture.prepOrders()

    orderType = BID
    fxpAmount = fix(1)
    fxpPrice = fix("0.6")
    outcome = 0
    tradeGroupID = 42

    assert cash.publicDepositEther(value = fix(10), sender = tester.k1) == 1, "Deposit cash"
    assert cash.approve(makeOrder.address, fix(10), sender = tester.k1) == 1, "Approve makeOrder contract to spend cash"
    makerInitialCash = cash.balanceOf(tester.a1)
    marketInitialCash = cash.balanceOf(market.address)
    with capture() as captured:
        orderID = makeOrder.publicMakeOrder(orderType, fxpAmount, fxpPrice, market.address, outcome, 0, 0, tradeGroupID, sender=tester.k1)
        logged = captured.stdout
    logMakeOrder = parseCapturedLogs(logged)[-1]
    assert orderID != 0, "Order ID should be non-zero"
    order = orders.getOrder(orderID, orderType, market.address, outcome)
    assert len(order) == 9, "Order array length should be 13"
    assert order[ATTOSHARES] == fxpAmount, "order[ATTOSHARES] should be the amount of the order"
    assert order[DISPLAY_PRICE] == fxpPrice, "order[DISPLAY_PRICE] should be the order's price"
    assert order[OWNER] == bytesToLong(tester.a1), "order[OWNER] should be the sender's address"
    assert order[OUTCOME] == outcome, "order[OUTCOME] should be the outcome ID"
    assert order[TOKENS_ESCROWED] == 0.6 * 10**18, "order[TOKENS_ESCROWED] should be the amount of money escrowed"
    assert order[SHARES_ESCROWED] == 0, "order[SHARES_ESCROWED] should be the number of shares escrowed"
    assert makerInitialCash - cash.balanceOf(tester.a1) == order[TOKENS_ESCROWED], "Decrease in maker's cash balance should equal money escrowed"
    assert cash.balanceOf(market.address) - marketInitialCash == order[TOKENS_ESCROWED], "Increase in market's cash balance should equal money escrowed"
    assert logMakeOrder["_event_type"] == "MakeOrder", "Should emit a MakeOrder event"
    assert logMakeOrder["tradeGroupID"] == tradeGroupID, "Logged tradeGroupID should match input"
    assert logMakeOrder["fxpMoneyEscrowed"] == order[TOKENS_ESCROWED], "Logged fxpMoneyEscrowed should match amount in order"
    assert logMakeOrder["fxpSharesEscrowed"] == order[SHARES_ESCROWED], "Logged fxpSharesEscrowed should match amount in order"
    assert logMakeOrder["timestamp"] == fixture.state.block.timestamp, "Logged timestamp should match the current block timestamp"
    assert logMakeOrder["orderID"] == longToHexString(orderID), "Logged orderID should match returned orderID"
    assert logMakeOrder["outcome"] == outcome, "Logged outcome should match input"
    assert logMakeOrder["market"] == longToHexString(market.address), "Logged market should match input"
    assert logMakeOrder["sender"] == bytesToHexString(tester.a1), "Logged sender should match input"

def test_make_ask_with_shares_take_with_shares():
    fixture = ContractsFixture()
    orders = fixture.initializeOrders()
    makeOrder = fixture.initializeMakeOrder()
    takeOrder = fixture.initializeTakeOrder()
    completeSets = fixture.initializeCompleteSets()
    branch = fixture.createBranch(0, 0)
    cash = fixture.uploadAndSeedCash()
    market = fixture.createReasonableBinaryMarket(branch, cash)
    yesShareToken = fixture.applySignature('shareToken', market.getShareToken(YES))
    noShareToken = fixture.applySignature('shareToken', market.getShareToken(NO))
    completeSetFees = fix(1.2) * 0.01 + fix(1.2) * 0.0001

    # 1. both accounts buy a complete set
    assert cash.publicDepositEther(value=fix(1.2), sender = tester.k1)
    assert cash.publicDepositEther(value=fix(1.2), sender = tester.k2)
    assert cash.approve(completeSets.address, fix(1.2), sender = tester.k1)
    assert cash.approve(completeSets.address, fix(1.2), sender = tester.k2)
    assert completeSets.publicBuyCompleteSets(market.address, fix(1.2), sender = tester.k1)
    assert completeSets.publicBuyCompleteSets(market.address, fix(1.2), sender = tester.k2)
    assert yesShareToken.balanceOf(tester.a1) == fix(1.2)
    assert yesShareToken.balanceOf(tester.a2) == fix(1.2)
    assert noShareToken.balanceOf(tester.a1) == fix(1.2)
    assert noShareToken.balanceOf(tester.a2) == fix(1.2)

    # 2. make ASK order for YES with YES shares for escrow
    assert yesShareToken.approve(makeOrder.address, fix(1.2), sender = tester.k1)
    askOrderID = makeOrder.publicMakeOrder(ASK, fix(1.2), fix(0.6), market.address, YES, 0, 0, 42, sender = tester.k1)
    assert askOrderID
    assert cash.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(0)
    assert noShareToken.balanceOf(tester.a1) == fix(1.2)

    # 3. take ASK order for YES with NO shares
    assert noShareToken.approve(takeOrder.address, fix(1.2), sender = tester.k2)
    fxpAmountRemaining = takeOrder.publicTakeOrder(askOrderID, ASK, market.address, YES, fix(1.2), sender = tester.k2)
    assert fxpAmountRemaining == 0
    assert cash.balanceOf(tester.a1) == fix(1.2) * 0.6
    assert cash.balanceOf(tester.a2) == fix(1.2) * 0.4 - completeSetFees
    assert yesShareToken.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a2) == fix(1.2)
    assert noShareToken.balanceOf(tester.a1) == fix(1.2)
    assert noShareToken.balanceOf(tester.a2) == fix(0)

def test_make_ask_with_shares_take_with_cash():
    fixture = ContractsFixture()
    orders = fixture.initializeOrders()
    makeOrder = fixture.initializeMakeOrder()
    takeOrder = fixture.initializeTakeOrder()
    completeSets = fixture.initializeCompleteSets()
    branch = fixture.createBranch(0, 0)
    cash = fixture.uploadAndSeedCash()
    market = fixture.createReasonableBinaryMarket(branch, cash)
    yesShareToken = fixture.applySignature('shareToken', market.getShareToken(YES))
    noShareToken = fixture.applySignature('shareToken', market.getShareToken(NO))

    # 1. buy a complete set with account 1
    assert cash.publicDepositEther(value=fix(1.2), sender = tester.k1)
    assert cash.approve(completeSets.address, fix(1.2), sender = tester.k1)
    assert completeSets.publicBuyCompleteSets(market.address, fix(1.2), sender = tester.k1)
    assert cash.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(1.2), "Account 1 should have fxpAmount shares of outcome 1"
    assert noShareToken.balanceOf(tester.a1) == fix(1.2), "Account 1 should have fxpAmount shares of outcome 2"

    # 2. make ASK order for YES with YES shares for escrow
    assert yesShareToken.approve(makeOrder.address, fix(1.2), sender = tester.k1)
    askOrderID = makeOrder.publicMakeOrder(ASK, fix(1.2), fix(0.6), market.address, YES, 0, 0, 42, sender = tester.k1)
    assert askOrderID, "Order ID should be non-zero"
    assert cash.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(0)
    assert noShareToken.balanceOf(tester.a1) == fix(1.2)

    # 3. take ASK order for YES with cash
    assert cash.publicDepositEther(value=long(fix(1.2) * 0.6), sender = tester.k2)
    assert cash.approve(takeOrder.address, long(fix(1.2) * 0.6), sender = tester.k2)
    fxpAmountRemaining = takeOrder.publicTakeOrder(askOrderID, ASK, market.address, YES, fix(1.2), sender = tester.k2)
    assert fxpAmountRemaining == 0
    assert cash.balanceOf(tester.a1) == fix(1.2) * 0.6
    assert cash.balanceOf(tester.a2) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a2) == fix(1.2)
    assert noShareToken.balanceOf(tester.a1) == fix(1.2)
    assert noShareToken.balanceOf(tester.a2) == fix(0)

def test_make_ask_with_cash_take_with_shares():
    fixture = ContractsFixture()
    orders = fixture.initializeOrders()
    makeOrder = fixture.initializeMakeOrder()
    takeOrder = fixture.initializeTakeOrder()
    completeSets = fixture.initializeCompleteSets()
    branch = fixture.createBranch(0, 0)
    cash = fixture.uploadAndSeedCash()
    market = fixture.createReasonableBinaryMarket(branch, cash)
    yesShareToken = fixture.applySignature('shareToken', market.getShareToken(YES))
    noShareToken = fixture.applySignature('shareToken', market.getShareToken(NO))

    # 1. buy complete sets with account 2
    assert cash.publicDepositEther(value=fix(1.2), sender = tester.k2)
    assert cash.approve(completeSets.address, fix(1.2), sender = tester.k2)
    assert completeSets.publicBuyCompleteSets(market.address, fix(1.2), sender = tester.k2)
    assert cash.balanceOf(tester.a2) == fix(0)
    assert yesShareToken.balanceOf(tester.a2) == fix(1.2)
    assert noShareToken.balanceOf(tester.a2) == fix(1.2)

    # 2. make ASK order for YES with cash escrowed
    assert cash.publicDepositEther(value=long(fix(1.2) * 0.4), sender = tester.k1)
    assert cash.approve(makeOrder.address, long(fix(1.2) * 0.4), sender = tester.k1)
    askOrderID = makeOrder.publicMakeOrder(ASK, fix(1.2), fix(0.6), market.address, YES, 0, 0, 42, sender = tester.k1)
    assert askOrderID
    assert cash.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(0)
    assert noShareToken.balanceOf(tester.a1) == fix(0)

    # 3. take ASK order for YES with shares of NO
    assert noShareToken.approve(takeOrder.address, fix(1.2), sender = tester.k2)
    fxpAmountRemaining = takeOrder.publicTakeOrder(askOrderID, ASK, market.address, YES, fix(1.2), sender = tester.k2)
    assert fxpAmountRemaining == 0, "Amount remaining should be 0"
    assert cash.balanceOf(tester.a1) == fix(0)
    assert cash.balanceOf(tester.a2) == fix(1.2) * 0.4
    assert yesShareToken.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a2) == fix(1.2)
    assert noShareToken.balanceOf(tester.a1) == fix(1.2)
    assert noShareToken.balanceOf(tester.a2) == fix(0)

def test_make_ask_with_cash_take_with_cash():
    fixture = ContractsFixture()
    orders = fixture.initializeOrders()
    makeOrder = fixture.initializeMakeOrder()
    takeOrder = fixture.initializeTakeOrder()
    completeSets = fixture.initializeCompleteSets()
    branch = fixture.createBranch(0, 0)
    cash = fixture.uploadAndSeedCash()
    market = fixture.createReasonableBinaryMarket(branch, cash)
    yesShareToken = fixture.applySignature('shareToken', market.getShareToken(YES))
    noShareToken = fixture.applySignature('shareToken', market.getShareToken(NO))

    # 1. make ASK order for YES with cash escrowed
    assert cash.publicDepositEther(value=long(fix(1.2) * 0.4), sender = tester.k1)
    assert cash.approve(makeOrder.address, long(fix(1.2) * 0.4), sender = tester.k1)
    askOrderID = makeOrder.publicMakeOrder(ASK, fix(1.2), fix(0.6), market.address, YES, 0, 0, 42, sender = tester.k1)
    assert askOrderID
    assert cash.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(0)
    assert noShareToken.balanceOf(tester.a1) == fix(0)

    # 2. take ASK order for YES with cash
    assert cash.publicDepositEther(value=long(fix(1.2) * 0.6), sender = tester.k2)
    assert cash.approve(takeOrder.address, long(fix(1.2) * 0.6), sender = tester.k2)
    fxpAmountRemaining = takeOrder.publicTakeOrder(askOrderID, ASK, market.address, YES, fix(1.2), sender = tester.k2)
    assert fxpAmountRemaining == 0
    assert cash.balanceOf(tester.a1) == fix(0)
    assert cash.balanceOf(tester.a2) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a2) == fix(1.2)
    assert noShareToken.balanceOf(tester.a1) == fix(1.2)
    assert noShareToken.balanceOf(tester.a2) == fix(0)

def test_make_bid_with_shares_take_with_shares():
    fixture = ContractsFixture()
    orders = fixture.initializeOrders()
    makeOrder = fixture.initializeMakeOrder()
    takeOrder = fixture.initializeTakeOrder()
    completeSets = fixture.initializeCompleteSets()
    branch = fixture.createBranch(0, 0)
    cash = fixture.uploadAndSeedCash()
    market = fixture.createReasonableBinaryMarket(branch, cash)
    yesShareToken = fixture.applySignature('shareToken', market.getShareToken(YES))
    noShareToken = fixture.applySignature('shareToken', market.getShareToken(NO))
    completeSetFees = fix(1.2) * 0.01 + fix(1.2) * 0.0001

    # 1. buy complete sets with both accounts
    assert cash.publicDepositEther(value=fix(1.2), sender = tester.k1) == 1
    assert cash.publicDepositEther(value=fix(1.2), sender = tester.k2) == 1
    assert cash.approve(completeSets.address, fix(1.2), sender = tester.k1)
    assert cash.approve(completeSets.address, fix(1.2), sender = tester.k2)
    assert completeSets.publicBuyCompleteSets(market.address, fix(1.2), sender = tester.k1)
    assert completeSets.publicBuyCompleteSets(market.address, fix(1.2), sender = tester.k2)
    assert cash.balanceOf(tester.a1) == fix(0)
    assert cash.balanceOf(tester.a2) == fix(0)
    assert yesShareToken.balanceOf(tester.a2) == fix(1.2)
    assert yesShareToken.balanceOf(tester.a1) == fix(1.2)
    assert noShareToken.balanceOf(tester.a1) == fix(1.2)
    assert noShareToken.balanceOf(tester.a2) == fix(1.2)

    # 2. make BID order for YES with NO shares escrowed
    assert noShareToken.approve(makeOrder.address, fix(1.2), sender = tester.k1)
    orderId = makeOrder.publicMakeOrder(BID, fix(1.2), fix(0.6), market.address, YES, 0, 0, 42, sender = tester.k1)
    assert orderId
    assert cash.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(1.2)
    assert noShareToken.balanceOf(tester.a1) == fix(0)

    # 3. take BID order for YES with shares of YES
    assert yesShareToken.approve(takeOrder.address, fix(1.2), sender = tester.k2)
    leftoverInOrder = takeOrder.publicTakeOrder(orderId, BID, market.address, YES, fix(1.2), sender = tester.k2)
    assert leftoverInOrder == 0
    assert cash.balanceOf(tester.a1) == fix(1.2) * 0.4
    assert cash.balanceOf(tester.a2) == fix(1.2) * 0.6 - completeSetFees
    assert yesShareToken.balanceOf(tester.a1) == fix(1.2)
    assert yesShareToken.balanceOf(tester.a2) == fix(0)
    assert noShareToken.balanceOf(tester.a1) == fix(0)
    assert noShareToken.balanceOf(tester.a2) == fix(1.2)

def test_make_bid_with_shares_take_with_cash():
    fixture = ContractsFixture()
    orders = fixture.initializeOrders()
    makeOrder = fixture.initializeMakeOrder()
    takeOrder = fixture.initializeTakeOrder()
    completeSets = fixture.initializeCompleteSets()
    branch = fixture.createBranch(0, 0)
    cash = fixture.uploadAndSeedCash()
    market = fixture.createReasonableBinaryMarket(branch, cash)
    yesShareToken = fixture.applySignature('shareToken', market.getShareToken(YES))
    noShareToken = fixture.applySignature('shareToken', market.getShareToken(NO))

    # 1. buy complete sets with account 1
    assert cash.publicDepositEther(value=fix(1.2), sender = tester.k1) == 1
    assert cash.approve(completeSets.address, fix(1.2), sender = tester.k1)
    assert completeSets.publicBuyCompleteSets(market.address, fix(1.2), sender = tester.k1)
    assert cash.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(1.2)
    assert noShareToken.balanceOf(tester.a1) == fix(1.2)

    # 2. make BID order for YES with NO shares escrowed
    assert noShareToken.approve(makeOrder.address, fix(1.2), sender = tester.k1)
    orderId = makeOrder.publicMakeOrder(BID, fix(1.2), fix(0.6), market.address, YES, 0, 0, 42, sender = tester.k1)
    assert orderId
    assert cash.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(1.2)
    assert noShareToken.balanceOf(tester.a1) == fix(0)

    # 3. take BID order for YES with cash
    assert cash.publicDepositEther(value=long(fix(1.2) * 0.4), sender = tester.k2) == 1
    assert cash.approve(takeOrder.address, long(fix(1.2) * 0.4), sender = tester.k2)
    leftoverInOrder = takeOrder.publicTakeOrder(orderId, BID, market.address, YES, fix(1.2), sender = tester.k2)
    assert leftoverInOrder == 0
    assert cash.balanceOf(tester.a1) == fix(1.2) * 0.4
    assert cash.balanceOf(tester.a2) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(1.2)
    assert yesShareToken.balanceOf(tester.a2) == fix(0)
    assert noShareToken.balanceOf(tester.a1) == fix(0)
    assert noShareToken.balanceOf(tester.a2) == fix(1.2)

def test_make_bid_with_cash_take_with_shares():
    fixture = ContractsFixture()
    orders = fixture.initializeOrders()
    makeOrder = fixture.initializeMakeOrder()
    takeOrder = fixture.initializeTakeOrder()
    completeSets = fixture.initializeCompleteSets()
    branch = fixture.createBranch(0, 0)
    cash = fixture.uploadAndSeedCash()
    market = fixture.createReasonableBinaryMarket(branch, cash)
    yesShareToken = fixture.applySignature('shareToken', market.getShareToken(YES))
    noShareToken = fixture.applySignature('shareToken', market.getShareToken(NO))

    # 1. buy complete sets with account 2
    assert cash.publicDepositEther(value=fix(1.2), sender = tester.k2) == 1
    assert cash.approve(completeSets.address, fix(1.2), sender = tester.k2)
    assert completeSets.publicBuyCompleteSets(market.address, fix(1.2), sender = tester.k2)
    assert cash.balanceOf(tester.a2) == fix(0)
    assert yesShareToken.balanceOf(tester.a2) == fix(1.2)
    assert noShareToken.balanceOf(tester.a2) == fix(1.2)

    # 2. make BID order for YES with cash escrowed
    assert cash.publicDepositEther(value=long(fix(1.2) * 0.6), sender = tester.k1) == 1
    assert cash.approve(makeOrder.address, long(fix(1.2) * 0.6), sender = tester.k1) == 1
    orderId = makeOrder.publicMakeOrder(BID, fix(1.2), fix(0.6), market.address, YES, 0, 0, 42, sender = tester.k1)
    assert orderId
    assert cash.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(0)
    assert noShareToken.balanceOf(tester.a1) == fix(0)

    # 3. take BID order for YES with shares of YES
    assert yesShareToken.approve(takeOrder.address, fix(1.2), sender = tester.k2)
    leftoverInOrder = takeOrder.publicTakeOrder(orderId, BID, market.address, YES, fix(1.2), sender = tester.k2)
    assert leftoverInOrder == 0
    assert cash.balanceOf(tester.a1) == fix(0)
    assert cash.balanceOf(tester.a2) == fix(1.2) * 0.6
    assert yesShareToken.balanceOf(tester.a1) == fix(1.2)
    assert yesShareToken.balanceOf(tester.a2) == fix(0)
    assert noShareToken.balanceOf(tester.a1) == fix(0)
    assert noShareToken.balanceOf(tester.a2) == fix(1.2)

def test_make_bid_with_cash_take_with_cash():
    fixture = ContractsFixture()
    orders = fixture.initializeOrders()
    makeOrder = fixture.initializeMakeOrder()
    takeOrder = fixture.initializeTakeOrder()
    completeSets = fixture.initializeCompleteSets()
    branch = fixture.createBranch(0, 0)
    cash = fixture.uploadAndSeedCash()
    market = fixture.createReasonableBinaryMarket(branch, cash)
    yesShareToken = fixture.applySignature('shareToken', market.getShareToken(YES))
    noShareToken = fixture.applySignature('shareToken', market.getShareToken(NO))

    # 2. make BID order for YES with cash escrowed
    assert cash.publicDepositEther(value=long(fix(1.2) * 0.6), sender = tester.k1) == 1
    assert cash.approve(makeOrder.address, long(fix(1.2) * 0.6), sender = tester.k1) == 1
    orderId = makeOrder.publicMakeOrder(BID, fix(1.2), fix(0.6), market.address, YES, 0, 0, 42, sender = tester.k1)
    assert orderId
    assert cash.balanceOf(tester.a1) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(0)
    assert noShareToken.balanceOf(tester.a1) == fix(0)

    # 3. take BID order for YES with cash
    assert cash.publicDepositEther(value=long(fix(1.2) * 0.4), sender = tester.k2) == 1
    assert cash.approve(takeOrder.address, long(fix(1.2) * 0.4), sender = tester.k2)
    leftoverInOrder = takeOrder.publicTakeOrder(orderId, BID, market.address, YES, fix(1.2), sender = tester.k2)
    assert leftoverInOrder == 0
    assert cash.balanceOf(tester.a1) == fix(0)
    assert cash.balanceOf(tester.a2) == fix(0)
    assert yesShareToken.balanceOf(tester.a1) == fix(1.2)
    assert yesShareToken.balanceOf(tester.a2) == fix(0)
    assert noShareToken.balanceOf(tester.a1) == fix(0)
    assert noShareToken.balanceOf(tester.a2) == fix(1.2)

# def test_ask_withPartialShares():
#     global shareTokenContractTranslator
#     outcomeShareContractWrapper = utils.makeOutcomeShareContractWrapper(contracts)
#     state.mine(1)
#     orderType = 2 # ask
#     fxpAmount = fix(1)
#     fxpPrice = fix("1.6")
#     outcome = 2
#     tradeGroupID = 42
#     eventID = utils.createEventType(contracts, marketType)
#     market.address = utils.createMarket(contracts, eventID)
#     utils.buyCompleteSets(contracts, market.address, fix(10))
#     fxpAmount = fix(12)
#     fxpAllowance = fix(120)
#     makerInitialCash = cash.balanceOf(tester.a1)
#     makerInitialShares = contracts.markets.getParticipantSharesPurchased(market.address, tester.a1, outcome)
#     marketInitialCash = cash.balanceOf(market)
#     marketInitialTotalShares = contracts.markets.getTotalSharesPurchased(market.address)
#     outcomeShareContract = contracts.markets.getOutcomeShareContract(market.address, outcome)
#     abiEncodedData = shareTokenContractTranslator.encode("approve", [makeOrder.address, fxpAllowance])
#     assert int(state.send(tester.k1, outcomeShareContract, 0, abiEncodedData).encode("hex"), 16) == 1, "Approve makeOrder contract to spend shares from the user's account (account 1)"
#     assert outcomeShareContractWrapper.allowance(outcomeShareContract, tester.a1, makeOrder.address) == fxpAllowance, "makeOrder contract's allowance should be equal to the amount approved"
#     assert cash.approve(makeOrder.address, fxpAllowance, sender=tester.k1) == 1, "Approve makeOrder contract to spend cash from account 1"
#     with iocapture.capture() as captured:
#         orderID = makeOrder.publicMakeOrder(orderType, fxpAmount, fxpPrice, market.address, outcome, 0, 0, tradeGroupID, sender=tester.k1)
#         logged = captured.stdout
#     logMakeOrder = parseCapturedLogs(logged)[-1]
#     assert orderID != 0, "Order ID should be non-zero"
#     order = orders.getOrder(orderID, orderType, market.address, outcome)
#     assert len(order) == 9, "Order array length should be 13"
#     assert order[0] == orderID, "order[0] should be the order ID"
#     assert order[1] == orderType, "order[1] should be the order type"
#     assert order[2] == market.address, "order[2] should be the market ID"
#     assert order[ATTOSHARES] == fxpAmount, "order[ATTOSHARES] should be the amount of the order"
#     assert order[DISPLAY_PRICE] == fxpPrice, "order[DISPLAY_PRICE] should be the order's price"
#     assert order[OWNER] == address1, "order[OWNER] should be the sender's address"
#     assert order[OUTCOME] == outcome, "order[6] should be the outcome ID"
#     assert order[TOKENS_ESCROWED] == int(unfix(fix(2)*(contracts.events.getMaxValue(eventID) - fxpPrice))), "order[TOKENS_ESCROWED] should be the amount of money escrowed"
#     assert order[SHARES_ESCROWED] == fix(10), "order[SHARES_ESCROWED] should be the number of shares escrowed"
#     assert makerInitialCash - cash.balanceOf(tester.a1) == order[TOKENS_ESCROWED], "Decrease in maker's cash balance should equal money escrowed"
#     assert cash.balanceOf(market) - marketInitialCash == order[TOKENS_ESCROWED], "Increase in market's cash balance should equal money escrowed"
#     assert logMakeOrder["_event_type"] == "MakeOrder", "Should emit a MakeOrder event"
#     assert logMakeOrder["tradeGroupID"] == tradeGroupID, "Logged tradeGroupID should match input"
#     assert logMakeOrder["fxpMoneyEscrowed"] == order[TOKENS_ESCROWED], "Logged fxpMoneyEscrowed should match amount in order"
#     assert logMakeOrder["fxpSharesEscrowed"] == order[SHARES_ESCROWED], "Logged fxpSharesEscrowed should match amount in order"
#     assert logMakeOrder["timestamp"] == state.block.timestamp, "Logged timestamp should match the current block timestamp"
#     assert logMakeOrder["orderID"] == orderID, "Logged orderID should match returned orderID"
#     assert logMakeOrder["outcome"] == outcome, "Logged outcome should match input"
#     assert logMakeOrder["market"] == market.address, "Logged market should match input"
#     assert logMakeOrder["sender"] == address1, "Logged sender should match input"

# def test_exceptions():
#     global shareTokenContractTranslator
#     outcomeShareContractWrapper = utils.makeOutcomeShareContractWrapper(contracts)
#     state.mine(1)
#     orderType = 1 # bid
#     fxpAmount = fix(1)
#     fxpPrice = fix("1.6")
#     outcome = 1
#     tradeGroupID = 42
#     eventID = utils.createBinaryEvent(contracts)
#     market.address = utils.createMarket(contracts, eventID)
#     makerInitialCash = cash.balanceOf(tester.a1)
#     marketInitialCash = cash.balanceOf(market)
#
#     # Permissions exceptions
#     state.mine(1)
#     try:
#         raise Exception(makeOrder.makeOrder(tester.a1, orderType, fxpAmount, fxpPrice, market.address, outcome, 0, 0, tradeGroupID, sender=tester.k1))
#     except Exception as exc:
#         assert isinstance(exc, ethereum.tester.TransactionFailed), "makeOrder should fail if called from a non-whitelisted account (account 1)"
#     try:
#         raise Exception(makeOrder.placeAsk(tester.a1, fxpAmount, fxpPrice, market.address, outcome, sender=tester.k1))
#     except Exception as exc:
#         assert isinstance(exc, ethereum.tester.TransactionFailed), "placeAsk should fail if called directly"
#     try:
#         raise Exception(makeOrder.placeBid(tester.a1, fxpAmount, fxpPrice, market.address, outcome, sender=tester.k1))
#     except Exception as exc:
#         assert isinstance(exc, ethereum.tester.TransactionFailed), "placeBid should fail if called directly"
#
#     # makeOrder exceptions (pre-placeBid/placeAsk)
#     state.mine(1)
#     try:
#         raise Exception(makeOrder.publicMakeOrder(orderType, fxpAmount, fxpPrice, market.address - 1, outcome, 0, 0, tradeGroupID, sender=tester.k1))
#     except Exception as exc:
#         assert isinstance(exc, ethereum.tester.TransactionFailed), "publicMakeOrder should fail if market ID is not valid"
#     try:
#         raise Exception(makeOrder.publicMakeOrder(3, fxpAmount, fxpPrice, market.address, outcome, 0, 0, tradeGroupID, sender=tester.k1))
#     except Exception as exc:
#         assert isinstance(exc, ethereum.tester.TransactionFailed), "publicMakeOrder should fail if order type is not 1 (bid) or 2 (ask)"
#
#     # placeBid exceptions
#     state.mine(1)
#     try:
#         raise Exception(makeOrder.publicMakeOrder(1, fxpAmount, fix(3), market.address, outcome, 0, 0, tradeGroupID, sender=tester.k1))
#     except Exception as exc:
#         assert isinstance(exc, ethereum.tester.TransactionFailed), "publicMakeOrder bid should fail if order cost per share is greater than the market's range"
#     try:
#         raise Exception(makeOrder.publicMakeOrder(1, 1, fxpPrice, market.address, outcome, 0, 0, tradeGroupID, sender=tester.k1))
#     except Exception as exc:
#         assert isinstance(exc, ethereum.tester.TransactionFailed), "publicMakeOrder bid should fail if order cost is below than the minimum order value"
#
#     # placeAsk exceptions
#     state.mine(1)
#     try:
#         raise Exception(makeOrder.publicMakeOrder(2, fxpAmount, 1, market.address, outcome, 0, 0, tradeGroupID, sender=tester.k1))
#     except Exception as exc:
#         assert isinstance(exc, ethereum.tester.TransactionFailed), "publicMakeOrder ask (without shares) should fail if order cost per share (maxValue - price) is greater than the market's range"
#     try:
#         raise Exception(makeOrder.publicMakeOrder(2, 1, fxpPrice, market.address, outcome, 0, 0, tradeGroupID, sender=tester.k1))
#     except Exception as exc:
#         assert isinstance(exc, ethereum.tester.TransactionFailed), "publicMakeOrder ask (without shares) should fail if order cost is below than the minimum order value"
#     utils.buyCompleteSets(contracts, market.address, fix(2))
#     state.mine(1)
#     try:
#         raise Exception(makeOrder.publicMakeOrder(2, fxpAmount, fix(3), market.address, outcome, 0, 0, tradeGroupID, sender=tester.k1))
#     except Exception as exc:
#         assert isinstance(exc, ethereum.tester.TransactionFailed), "publicMakeOrder ask (with shares held) should fail if cost per share (price - minValue) is greater than the market's range"
#     try:
#         raise Exception(makeOrder.publicMakeOrder(2, 1, fxpPrice, market.address, outcome, 0, 0, tradeGroupID, sender=tester.k1))
#     except Exception as exc:
#         assert isinstance(exc, ethereum.tester.TransactionFailed), "publicMakeOrder ask (with shares held) should fail if order cost is below than the minimum order value"
#
#     state.mine(1)
#     assert cash.approve(makeOrder.address, fix(100), sender=tester.k1) == 1, "Approve makeOrder contract to spend cash from account 1"
#     fxpAllowance = fix(12)
#     outcomeTwoShareContract = contracts.markets.getOutcomeShareContract(market.address, 2)
#     abiEncodedData = shareTokenContractTranslator.encode("approve", [makeOrder.address, fxpAllowance])
#     assert int(state.send(tester.k1, outcomeTwoShareContract, 0, abiEncodedData).encode("hex"), 16) == 1, "Approve makeOrder contract to spend shares from the user's account (account 1)"
#     assert outcomeShareContractWrapper.allowance(outcomeTwoShareContract, tester.a1, makeOrder.address) == fxpAllowance, "makeOrder contract's allowance should be equal to the amount approved"
#     state.mine(1)
#     assert makeOrder.publicMakeOrder(orderType, fxpAmount, fxpPrice, market.address, outcome, 0, 0, tradeGroupID, sender=tester.k1) != 0, "Order ID should be non-zero"
#
#     # makeOrder exceptions (post-placeBid/Ask)
#     try:
#         raise Exception(makeOrder.publicMakeOrder(orderType, fxpAmount, fxpPrice, market.address, outcome, 0, 0, tradeGroupID, sender=tester.k1))
#     except Exception as exc:
#         assert isinstance(exc, ethereum.tester.TransactionFailed), "publicMakeOrder should fail if duplicate orders are placed in the same block (should combine into a single order instead)"
