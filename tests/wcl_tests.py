#!/usr/bin/env python
from __future__ import division
import math
import random
import os
import sys
import ethereum.tester
import utils
from decimal import *

shareTokenContractTranslator = ethereum.abi.ContractTranslator('[{"constant": false, "type": "function", "name": "allowance(address,address)", "outputs": [{"type": "int256", "name": "out"}], "inputs": [{"type": "address", "name": "owner"}, {"type": "address", "name": "spender"}]}, {"constant": false, "type": "function", "name": "approve(address,uint256)", "outputs": [{"type": "int256", "name": "out"}], "inputs": [{"type": "address", "name": "spender"}, {"type": "uint256", "name": "value"}]}, {"constant": false, "type": "function", "name": "balanceOf(address)", "outputs": [{"type": "int256", "name": "out"}], "inputs": [{"type": "address", "name": "address"}]}, {"constant": false, "type": "function", "name": "changeTokens(int256,int256)", "outputs": [{"type": "int256", "name": "out"}], "inputs": [{"type": "int256", "name": "trader"}, {"type": "int256", "name": "amount"}]}, {"constant": false, "type": "function", "name": "createShares(address,uint256)", "outputs": [{"type": "int256", "name": "out"}], "inputs": [{"type": "address", "name": "owner"}, {"type": "uint256", "name": "fxpValue"}]}, {"constant": false, "type": "function", "name": "destroyShares(address,uint256)", "outputs": [{"type": "int256", "name": "out"}], "inputs": [{"type": "address", "name": "owner"}, {"type": "uint256", "name": "fxpValue"}]}, {"constant": false, "type": "function", "name": "getDecimals()", "outputs": [{"type": "int256", "name": "out"}], "inputs": []}, {"constant": false, "type": "function", "name": "getName()", "outputs": [{"type": "int256", "name": "out"}], "inputs": []}, {"constant": false, "type": "function", "name": "getSymbol()", "outputs": [{"type": "int256", "name": "out"}], "inputs": []}, {"constant": false, "type": "function", "name": "modifySupply(int256)", "outputs": [{"type": "int256", "name": "out"}], "inputs": [{"type": "int256", "name": "amount"}]}, {"constant": false, "type": "function", "name": "setController(address)", "outputs": [{"type": "int256", "name": "out"}], "inputs": [{"type": "address", "name": "newController"}]}, {"constant": false, "type": "function", "name": "suicideFunds(address)", "outputs": [], "inputs": [{"type": "address", "name": "to"}]}, {"constant": false, "type": "function", "name": "totalSupply()", "outputs": [{"type": "int256", "name": "out"}], "inputs": []}, {"constant": false, "type": "function", "name": "transfer(address,uint256)", "outputs": [{"type": "int256", "name": "out"}], "inputs": [{"type": "address", "name": "to"}, {"type": "uint256", "name": "value"}]}, {"constant": false, "type": "function", "name": "transferFrom(address,address,uint256)", "outputs": [{"type": "int256", "name": "out"}], "inputs": [{"type": "address", "name": "from"}, {"type": "address", "name": "to"}, {"type": "uint256", "name": "value"}]}, {"inputs": [{"indexed": true, "type": "address", "name": "owner"}, {"indexed": true, "type": "address", "name": "spender"}, {"indexed": false, "type": "uint256", "name": "value"}], "type": "event", "name": "Approval(address,address,uint256)"}, {"inputs": [{"indexed": true, "type": "address", "name": "from"}, {"indexed": true, "type": "address", "name": "to"}, {"indexed": false, "type": "uint256", "name": "value"}], "type": "event", "name": "Transfer(address,address,uint256)"}, {"inputs": [{"indexed": false, "type": "int256", "name": "from"}, {"indexed": false, "type": "int256", "name": "to"}, {"indexed": false, "type": "int256", "name": "value"}, {"indexed": false, "type": "int256", "name": "senderBalance"}, {"indexed": false, "type": "int256", "name": "sender"}, {"indexed": false, "type": "int256", "name": "spenderMaxValue"}], "type": "event", "name": "echo(int256,int256,int256,int256,int256,int256)"}]')

# bid assertions
def assertions_bid_makerEscrowedCash_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID):
    fxpMinValue = contracts.events.getMinValue(eventID)
    fxpMaxValue = contracts.events.getMaxValue(eventID)
    numOutcomes = contracts.events.getNumOutcomes(eventID)
    makerFinalCash = contracts.cash.balanceOf(MAKER)
    takerFinalCash = contracts.cash.balanceOf(TAKER)
    marketFinalCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
    if numOutcomes > 2:
        # categorical, max is forced to 2 for calculations
        fxpMaxValue = utils.fix(2)
    # Low Side = (price - min)*amount
    expectedMakerCost = calculateLowSide(contracts, eventID, fxpAmount, fxpPrice)
    # High Side = (max - price)*amount
    expectedTakerCost = calculateHighSide(contracts, eventID, fxpAmount, fxpPrice)
    assert(marketFinalCash == (marketInitialCash + ((fxpMaxValue - fxpMinValue)*utils.unfix(fxpAmount)))), "Market's cash balance should be the marketInitialCash + (max - min)*amount of the maker's Order"
    assert(makerFinalCash == makerInitialCash - expectedMakerCost), "maker's cash balance should be maker's initial balance - (price-min)*amount"
    assert(takerFinalCash == takerInitialCash - expectedTakerCost), "taker's cash balance should be taker's initial balance - (max-price)*amountTakerWanted"
    # create expected shares output
    makerExpectedShares = []
    takerExpectedShares = []
    for i in range(0, numOutcomes):
        outcome = i + 1
        if outcome == outcomeID:
            makerExpectedShares.append(fxpAmount)
        else:
            makerExpectedShares.append(0)
    for i in range(0, numOutcomes):
        outcome = i + 1
        if outcome != outcomeID:
            takerExpectedShares.append(fxpAmount)
        else:
            takerExpectedShares.append(0)
    # confirm shares
    check_shares(contracts, marketID, MAKER, makerExpectedShares)
    check_shares(contracts, marketID, TAKER, takerExpectedShares)

def assertions_bid_makerEscrowedShares_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID):
    fxpMinValue = contracts.events.getMinValue(eventID)
    fxpMaxValue = contracts.events.getMaxValue(eventID)
    numOutcomes = contracts.events.getNumOutcomes(eventID)
    makerFinalCash = contracts.cash.balanceOf(MAKER)
    takerFinalCash = contracts.cash.balanceOf(TAKER)
    marketFinalCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
    if numOutcomes > 2:
        # categorical, max is forced to 2 for calculations
        fxpMaxValue = utils.fix(2)
    # Low Side = (price - min)*amount
    fxpExpectedMakerCost = calculateLowSide(contracts, eventID, fxpAmount, fxpPrice)
    # High Side = (max - price)*amount
    fxpExpectedTakerCost = calculateHighSide(contracts, eventID, fxpAmount, fxpPrice)
    fxpCumulativeScale = contracts.markets.getCumulativeScale(marketID)
    fxpTradingFee = contracts.markets.getTradingFee(marketID)
    fxpExpectedFee = int(Decimal(fxpTradingFee) * fxpAmount / Decimal(10)**Decimal(18) * fxpCumulativeScale / Decimal(10)**Decimal(18))
    fxpExpectedFeePaidToCreator = int(Decimal(fxpExpectedFee) / Decimal(2))
    marketCreator = contracts.info.getCreator(marketID)
    if marketCreator == MAKER.encode('hex'):
        # maker gets fxpExpectedFeePaidToCreator as well
        assert(makerFinalCash == makerInitialCash + fxpExpectedTakerCost - fxpExpectedFee + fxpExpectedFeePaidToCreator), "Maker's final cash balance should be makerInitialCash + (max-price)*amount - ((fxpTradingFee*amount*marketCumlativeScale) /2)"
    else:
        assert(makerFinalCash == makerInitialCash + fxpExpectedTakerCost - fxpExpectedFee), "Maker's final cash balance should be makerInitialCash + (max-price)*amount - (fxpTradingFee*amount*marketCumlativeScale)"
    assert(takerFinalCash == takerInitialCash + fxpExpectedMakerCost), "Taker's final cash balance takerInitialCash + (price - min)*amount"
    assert(marketFinalCash == marketInitialCash - (fxpExpectedTakerCost + fxpExpectedMakerCost) + (fxpExpectedFee - fxpExpectedFeePaidToCreator)), "Market's final cash balance should be marketInitialCash - ((max - min)*amount) + ((fxpTradingFee*amount*marketCumlativeScale) / 2)"
    # create expected shares output
    makerExpectedShares = []
    takerExpectedShares = []
    for i in range(0, numOutcomes):
        makerExpectedShares.append(0)
    for i in range(0, numOutcomes):
        takerExpectedShares.append(0)
    # confirm shares
    check_shares(contracts, marketID, MAKER, makerExpectedShares)
    check_shares(contracts, marketID, TAKER, takerExpectedShares)

def assertions_bid_makerEscrowedCash_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID):
    fxpMinValue = contracts.events.getMinValue(eventID)
    fxpMaxValue = contracts.events.getMaxValue(eventID)
    numOutcomes = contracts.events.getNumOutcomes(eventID)
    makerFinalCash = contracts.cash.balanceOf(MAKER)
    takerFinalCash = contracts.cash.balanceOf(TAKER)
    marketFinalCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
    if numOutcomes > 2:
        # categorical, max is forced to 2 for calculations
        fxpMaxValue = utils.fix(2)
    # Low Side = (price - min)*amount
    fxpExpectedTakerGain = calculateLowSide(contracts, eventID, fxpAmount, fxpPrice)
    assert(makerFinalCash == makerInitialCash - fxpExpectedTakerGain), "Maker's Final cash balance should be makerInitialCash - ((price - min)*amount)"
    assert(takerFinalCash == takerInitialCash + fxpExpectedTakerGain), "Taker's Final cash balance should be makerInitialCash + ((price - min)*amount)"
    assert(marketFinalCash == marketInitialCash), "Market's Final cash balance should be marketInitialCash. (unchanged balance)"
    # create expected shares output
    makerExpectedShares = []
    takerExpectedShares = []
    for i in range(0, numOutcomes):
        outcome = i + 1
        if outcome == outcomeID:
            makerExpectedShares.append(fxpAmount)
        else:
            makerExpectedShares.append(0)
    for i in range(0, numOutcomes):
        outcome = i + 1
        if outcome != outcomeID:
            takerExpectedShares.append(fxpAmount)
        else:
            takerExpectedShares.append(0)
    # confirm shares
    check_shares(contracts, marketID, MAKER, makerExpectedShares)
    check_shares(contracts, marketID, TAKER, takerExpectedShares)

def assertions_bid_makerEscrowedShares_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID):
    fxpMinValue = contracts.events.getMinValue(eventID)
    fxpMaxValue = contracts.events.getMaxValue(eventID)
    numOutcomes = contracts.events.getNumOutcomes(eventID)
    makerFinalCash = contracts.cash.balanceOf(MAKER)
    takerFinalCash = contracts.cash.balanceOf(TAKER)
    marketFinalCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
    if numOutcomes > 2:
        # categorical, max is forced to 2 for calculations
        fxpMaxValue = utils.fix(2)
    # High Side = (max - price)*amount
    fxpExpectedTakerCost = calculateHighSide(contracts, eventID, fxpAmount, fxpPrice)
    fxpCumulativeScale = contracts.markets.getCumulativeScale(marketID)
    fxpTradingFee = contracts.markets.getTradingFee(marketID)
    fxpExpectedFee = int(Decimal(fxpTradingFee) * fxpAmount / Decimal(10)**Decimal(18) * fxpCumulativeScale / Decimal(10)**Decimal(18))
    # note: creator is also maker in this case
    fxpExpectedFeePaidToCreator = int(Decimal(fxpExpectedFee) / Decimal(2))
    marketCreator = contracts.info.getCreator(marketID)
    if marketCreator == MAKER.encode('hex'):
        assert(makerFinalCash == makerInitialCash + fxpExpectedTakerCost - fxpExpectedFee + fxpExpectedFeePaidToCreator), "Maker's final cash balance should be makerInitialCash + ((max*price)*amount) + ((fxpTradingFee*amount*marketCumlativeScale) / 2)"
    else:
        assert(makerFinalCash == makerInitialCash + fxpExpectedTakerCost - fxpExpectedFee), "Maker's final cash balance should be makerInitialCash + ((max*price)*amount) - (fxpTradingFee*amount*marketCumlativeScale)"
    assert(takerFinalCash == takerInitialCash - fxpExpectedTakerCost), "Taker's final cash balance takerInitialCash - ((max-price)*amount)"
    assert(marketFinalCash == marketInitialCash + (fxpExpectedFee - fxpExpectedFeePaidToCreator)), "Market's final cash balance should be marketInitialCash + ((fxpTradingFee*amount*marketCumlativeScale) / 2)"
    # create expected shares output
    makerExpectedShares = []
    takerExpectedShares = []
    for i in range(0, numOutcomes):
        makerExpectedShares.append(0)
    for i in range(0, numOutcomes):
        outcome = i + 1
        if outcome != outcomeID:
            takerExpectedShares.append(fxpAmount)
        else:
            takerExpectedShares.append(0)
    # confirm shares
    check_shares(contracts, marketID, MAKER, makerExpectedShares)
    check_shares(contracts, marketID, TAKER, takerExpectedShares)

# ask assertions
def assertions_ask_makerEscrowedCash_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID):
    fxpMinValue = contracts.events.getMinValue(eventID)
    fxpMaxValue = contracts.events.getMaxValue(eventID)
    numOutcomes = contracts.events.getNumOutcomes(eventID)
    makerFinalCash = contracts.cash.balanceOf(MAKER)
    takerFinalCash = contracts.cash.balanceOf(TAKER)
    marketFinalCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
    if numOutcomes > 2:
        # categorical, max is forced to 2 for calculations
        fxpMaxValue = utils.fix(2)
    # Low Side = (price - min)*amount
    expectedTakerCost = calculateLowSide(contracts, eventID, fxpAmount, fxpPrice)
    # High Side = (max - price)*amount
    expectedMakerCost = calculateHighSide(contracts, eventID, fxpAmount, fxpPrice)
    assert(marketFinalCash == marketInitialCash + (expectedMakerCost + expectedTakerCost)), "Market's cash balance should be the marketInitialCash + (max - min)*amount"
    assert(makerFinalCash == makerInitialCash - expectedMakerCost), "maker's cash balance should be maker's initial balance - (max - price)*amount"
    assert(takerFinalCash == takerInitialCash - expectedTakerCost), "taker's cash balance should be taker's initial balance - (max - price)*amount"
    # create expected shares output
    makerExpectedShares = []
    takerExpectedShares = []
    for i in range(0, numOutcomes):
        outcome = i + 1
        if outcome != outcomeID:
            makerExpectedShares.append(fxpAmount)
        else:
            makerExpectedShares.append(0)
    for i in range(0, numOutcomes):
        outcome = i + 1
        if outcome == outcomeID:
            takerExpectedShares.append(fxpAmount)
        else:
            takerExpectedShares.append(0)
    # confirm shares
    check_shares(contracts, marketID, MAKER, makerExpectedShares)
    check_shares(contracts, marketID, TAKER, takerExpectedShares)

def assertions_ask_makerEscrowedShares_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID):
    fxpMinValue = contracts.events.getMinValue(eventID)
    fxpMaxValue = contracts.events.getMaxValue(eventID)
    numOutcomes = contracts.events.getNumOutcomes(eventID)
    makerFinalCash = contracts.cash.balanceOf(MAKER)
    takerFinalCash = contracts.cash.balanceOf(TAKER)
    marketFinalCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
    if numOutcomes > 2:
        # categorical, max is forced to 2 for calculations
        fxpMaxValue = utils.fix(2)
    # Low Side = (price - min)*amount
    fxpExpectedMakerGain = calculateLowSide(contracts, eventID, fxpAmount, fxpPrice)
    # High Side = (max - price)*amount
    fxpExpectedTakerGain = calculateHighSide(contracts, eventID, fxpAmount, fxpPrice)
    fxpCumulativeScale = contracts.markets.getCumulativeScale(marketID)
    fxpTradingFee = contracts.markets.getTradingFee(marketID)
    fxpExpectedFee = int(Decimal(fxpTradingFee) * fxpAmount / Decimal(10)**Decimal(18) * fxpCumulativeScale / Decimal(10)**Decimal(18))
    fxpExpectedFeePaidToCreator = int(Decimal(fxpExpectedFee) / Decimal(2))
    marketCreator = contracts.info.getCreator(marketID)
    if marketCreator == MAKER.encode('hex'):
        # maker is also market creator
        assert(makerFinalCash == makerInitialCash + fxpExpectedMakerGain + fxpExpectedFeePaidToCreator), "Maker's final cash balance should be makerInitialCash + (price - min)*amount + ((fxpTradingFee*amount) / 2)"
    else:
        assert(makerFinalCash == makerInitialCash + fxpExpectedMakerGain), "Maker's final cash balance should be makerInitialCash + (price - min)*amount"
    assert(takerFinalCash == takerInitialCash + fxpExpectedTakerGain - fxpExpectedFee), "Taker's final cash balance takerInitialCash + (max-price)*amount - fxpTradingFee*amount"
    assert(marketFinalCash == (marketInitialCash - ((fxpExpectedMakerGain + fxpExpectedTakerGain) - (fxpExpectedFee - fxpExpectedFeePaidToCreator)))), "Market's final cash balance should be marketInitialCash - ((max-min)*amount - ((fxpTradingFee*amount) / 2))"
    # create expected shares output
    makerExpectedShares = []
    takerExpectedShares = []
    for i in range(0, numOutcomes):
        makerExpectedShares.append(0)
    for i in range(0, numOutcomes):
        takerExpectedShares.append(0)
    # confirm shares
    check_shares(contracts, marketID, MAKER, makerExpectedShares)
    check_shares(contracts, marketID, TAKER, takerExpectedShares)

def assertions_ask_makerEscrowedCash_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID):
    fxpMinValue = contracts.events.getMinValue(eventID)
    fxpMaxValue = contracts.events.getMaxValue(eventID)
    numOutcomes = contracts.events.getNumOutcomes(eventID)
    makerFinalCash = contracts.cash.balanceOf(MAKER)
    takerFinalCash = contracts.cash.balanceOf(TAKER)
    marketFinalCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
    if numOutcomes > 2:
        # categorical, max is forced to 2 for calculations
        fxpMaxValue = utils.fix(2)
    # High Side = (max - price)*amount
    fxpExpectedTakerGain = calculateHighSide(contracts, eventID, fxpAmount, fxpPrice)
    fxpCumulativeScale = contracts.markets.getCumulativeScale(marketID)
    fxpTradingFee = contracts.markets.getTradingFee(marketID)
    fxpExpectedFee = int(Decimal(fxpTradingFee) * fxpAmount / Decimal(10)**Decimal(18) * fxpCumulativeScale / Decimal(10)**Decimal(18))
    fxpExpectedFeePaidToCreator = int(Decimal(fxpExpectedFee) / Decimal(2))
    marketCreator = contracts.info.getCreator(marketID)
    if marketCreator == MAKER.encode('hex'):
        # maker is also market creator
        assert(makerFinalCash == makerInitialCash - fxpExpectedTakerGain + fxpExpectedFeePaidToCreator), "maker final cash should be equal to makerInitialCash - (max - price)*amount + ((fxpTradingFee*amount) / 2))."
    else:
        assert(makerFinalCash == makerInitialCash - fxpExpectedTakerGain), "maker final cash should be equal to makerInitialCash - (max - price)*amount."
    assert(takerFinalCash == takerInitialCash + fxpExpectedTakerGain - fxpExpectedFee), "taker final cash should be equal to takerInitialCash + (max - price)*amount - (fxpTradingFee*amount)"
    assert(marketFinalCash == marketInitialCash + fxpExpectedFee - fxpExpectedFeePaidToCreator), "market final cash should be equal to marketInitialCash + ((fxpTradingFee*amount) / 2))"
    # create expected shares output
    makerExpectedShares = []
    takerExpectedShares = []
    for i in range(0, numOutcomes):
        outcome = i + 1
        if outcome != outcomeID:
            makerExpectedShares.append(fxpAmount)
        else:
            makerExpectedShares.append(0)
    for i in range(0, numOutcomes):
        outcome = i + 1
        if outcome == outcomeID:
            takerExpectedShares.append(fxpAmount)
        else:
            takerExpectedShares.append(0)
    # confirm shares
    check_shares(contracts, marketID, MAKER, makerExpectedShares)
    check_shares(contracts, marketID, TAKER, takerExpectedShares)

def assertions_ask_makerEscrowedShares_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID):
    fxpMinValue = contracts.events.getMinValue(eventID)
    fxpMaxValue = contracts.events.getMaxValue(eventID)
    numOutcomes = contracts.events.getNumOutcomes(eventID)
    makerFinalCash = contracts.cash.balanceOf(MAKER)
    takerFinalCash = contracts.cash.balanceOf(TAKER)
    marketFinalCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
    if numOutcomes > 2:
        # categorical, max is forced to 2 for calculations
        fxpMaxValue = utils.fix(2)
    # Low Side = (price - min)*amount
    fxpExpectedMakerGain = calculateLowSide(contracts, eventID, fxpAmount, fxpPrice)
    assert(makerFinalCash == makerInitialCash + fxpExpectedMakerGain), "Maker's final cash balance should be makerInitialCash + fxpExpectedMakerGain"
    assert(takerFinalCash == takerInitialCash - fxpExpectedMakerGain), "Taker's final cash balance takerInitialCash - fxpExpectedMakerGain"
    assert(marketFinalCash == marketInitialCash), "Market's final cash balance should be marketInitialCash"
    # create expected shares output
    makerExpectedShares = []
    takerExpectedShares = []
    for i in range(0, numOutcomes):
        makerExpectedShares.append(0)
    for i in range(0, numOutcomes):
        outcome = i + 1
        if outcome == outcomeID:
            takerExpectedShares.append(fxpAmount)
        else:
            takerExpectedShares.append(0)
    # confirm shares
    check_shares(contracts, marketID, MAKER, makerExpectedShares)
    check_shares(contracts, marketID, TAKER, takerExpectedShares)

# bid order tests
def test_bidOrders(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY):
    def test_makerEscrowedCash_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY):
        # maker escrows cash, taker does not have shares of anything
        t = contracts._ContractLoader__tester
        contracts._ContractLoader__state.mine(1)
        orderType = 1 # bid
        fxpExpectedMakerCost = calculateLowSide(contracts, eventID, fxpAmount, fxpPrice)
        outcomeID = 2
        tradeGroupID = 10
        # get initial cash
        makerInitialCash = contracts.cash.balanceOf(MAKER)
        takerInitialCash = contracts.cash.balanceOf(TAKER)
        marketInitialCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
        # Start makeOrder
        orderID = contracts.makeOrder.publicMakeOrder(orderType, fxpAmount, fxpPrice, marketID, outcomeID, 0, 0, tradeGroupID, sender=MAKER_KEY)
        # assert order and market cash
        order = contracts.orders.getOrder(orderID, orderType, marketID, outcomeID)
        assert(contracts.cash.balanceOf(contracts.info.getWallet(marketID)) - marketInitialCash == order[8]), "Increase in market's cash balance should equal money escrowed"
        assert(contracts.cash.balanceOf(contracts.info.getWallet(marketID)) == marketInitialCash + fxpExpectedMakerCost), "Market's cash balance should be marketInitialCash + (price - min)*amount"
        contracts._ContractLoader__state.mine(1)
        # Start takeOrder
        fxpAmountRemaining = contracts.takeOrder.publicTakeOrder(orderID, orderType, marketID, outcomeID, fxpAmount, sender=TAKER_KEY)
        # Final Assertions
        assert(fxpAmountRemaining == 0), "Amount remaining should be 0"
        assertions_bid_makerEscrowedCash_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID)
    def test_makerEscrowedShares_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY):
        # maker has shares in other outcomes, taker has shares of outcome
        t = contracts._ContractLoader__tester
        contracts._ContractLoader__state.mine(1)
        orderType = 1 # bid
        outcomeID = 1
        tradeGroupID = 10
        numOutcomes = contracts.markets.getMarketNumOutcomes(marketID)
        # make sure maker only has outcomeID shares...
        for i in range(0, numOutcomes):
            curOutcome = i + 1
            if (contracts.markets.getParticipantSharesPurchased(marketID, TAKER, curOutcome) > 0 and curOutcome != outcomeID):
                send_shares(contracts, marketID, TAKER, TAKER_KEY, curOutcome, MAKER)
        contracts._ContractLoader__state.mine(1)
        # get initial cash and shares
        makerInitialCash = contracts.cash.balanceOf(MAKER)
        takerInitialCash = contracts.cash.balanceOf(TAKER)
        marketInitialCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
        makerInitialShares = contracts.markets.getParticipantSharesPurchased(marketID, MAKER, 2)
        # Start makeOrder
        orderID = contracts.makeOrder.publicMakeOrder(orderType, fxpAmount, fxpPrice, marketID, outcomeID, 0, 0, tradeGroupID, sender=MAKER_KEY)
        # assert order and market cash
        order = contracts.orders.getOrder(orderID, orderType, marketID, outcomeID)
        assert(makerInitialShares == order[9]), "Shares Escrowed should be = to the shares the maker started with"
        assert(makerInitialShares - order[9] == contracts.markets.getParticipantSharesPurchased(marketID, MAKER, 2)), "maker shouldn't have shares in outcomeID anymore"
        contracts._ContractLoader__state.mine(1)
        fxpAmountRemaining = contracts.takeOrder.publicTakeOrder(orderID, orderType, marketID, outcomeID, fxpAmount, sender=TAKER_KEY)
        # Final Assertions
        assert(fxpAmountRemaining == 0), "Amount remaining should be 0"
        assertions_bid_makerEscrowedShares_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID)
    def test_makerEscrowedCash_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY):
        # maker escrows cash, taker has complete set
        t = contracts._ContractLoader__tester
        contracts._ContractLoader__state.mine(1)
        orderType = 1 # bid
        outcomeID = 2
        tradeGroupID = 10
        # taker first buys a complete set
        # buy the amount the taker plans to take from the order
        contracts._ContractLoader__state.mine(1)
        utils.buyCompleteSets(contracts, marketID, fxpAmount, TAKER_KEY)
        contracts._ContractLoader__state.mine(1)
        # get initial cash
        makerInitialCash = contracts.cash.balanceOf(MAKER)
        takerInitialCash = contracts.cash.balanceOf(TAKER)
        marketInitialCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
        # Start makeOrder
        orderID = contracts.makeOrder.publicMakeOrder(orderType, fxpAmount, fxpPrice, marketID, outcomeID, 0, 0, tradeGroupID, sender=MAKER_KEY)
        order = contracts.orders.getOrder(orderID, orderType, marketID, outcomeID)
        # assert order and market cash
        assert(contracts.cash.balanceOf(contracts.info.getWallet(marketID)) - marketInitialCash == order[8]), "Increase in market's cash balance should equal money escrowed"
        contracts._ContractLoader__state.mine(1)
        # Start takeOrder
        fxpAmountRemaining = contracts.takeOrder.publicTakeOrder(orderID, orderType, marketID, outcomeID, fxpAmount, sender=TAKER_KEY)
        # Final Assertions
        assert(fxpAmountRemaining == 0), "Amount remaining should be 0"
        assertions_bid_makerEscrowedCash_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID)
    def test_makerEscrowedShares_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY):
        # maker has shares in other outcome, taker has shares in outcome
        t = contracts._ContractLoader__tester
        contracts._ContractLoader__state.mine(1)
        orderType = 1 # bid
        outcomeID = 1
        tradeGroupID = 10
        numOutcomes = contracts.markets.getMarketNumOutcomes(marketID)
        # make sure maker shares in all outcomes except outcomeID (1)
        for i in range(0, numOutcomes):
            curOutcome = i + 1
            if (contracts.markets.getParticipantSharesPurchased(marketID, TAKER, curOutcome) > 0 and curOutcome != outcomeID):
                send_shares(contracts, marketID, TAKER, TAKER_KEY, curOutcome, MAKER)
        # transfer shares from taker to account 0 if taker has any shares
        # this is done because taker should still have shares of outcomeID (1)
        send_shares(contracts, marketID, TAKER, TAKER_KEY)
        contracts._ContractLoader__state.mine(1)
        # get initial cash & shares
        makerInitialCash = contracts.cash.balanceOf(MAKER)
        takerInitialCash = contracts.cash.balanceOf(TAKER)
        marketInitialCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
        makerInitialShares = contracts.markets.getParticipantSharesPurchased(marketID, MAKER, 2)
        # Start makeOrder
        orderID = contracts.makeOrder.publicMakeOrder(orderType, fxpAmount, fxpPrice, marketID, outcomeID, 0, 0, tradeGroupID, sender=MAKER_KEY)
        # assert order and market cash
        order = contracts.orders.getOrder(orderID, orderType, marketID, outcomeID)
        assert(makerInitialShares == order[9]), "Shares Escrowed should be = to the shares the maker started with"
        assert(makerInitialShares - order[9] == contracts.markets.getParticipantSharesPurchased(marketID, MAKER, 2)), "maker shouldn't have shares in outcomeID anymore"
        contracts._ContractLoader__state.mine(1)
        # Start takeOrder
        fxpAmountRemaining = contracts.takeOrder.publicTakeOrder(orderID, orderType, marketID, outcomeID, fxpAmount, sender=TAKER_KEY)
        # Final Assertions
        assert(fxpAmountRemaining == 0), "Amount remaining should be 0"
        assertions_bid_makerEscrowedShares_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID)
        # finally, transfer all shares to account 0 to close out binary bid tests
        send_shares(contracts, marketID, MAKER, MAKER_KEY)
        send_shares(contracts, marketID, TAKER, TAKER_KEY)
    test_makerEscrowedCash_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    test_makerEscrowedShares_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    test_makerEscrowedCash_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    test_makerEscrowedShares_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)

# ask order tests
def test_askOrders(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY):
    def test_makerEscrowedCash_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY):
        # maker has cash, taker has cash
        t = contracts._ContractLoader__tester
        contracts._ContractLoader__state.mine(1)
        orderType = 2 # ask
        fxpExpectedCash = calculateHighSide(contracts, eventID, fxpAmount, fxpPrice)
        outcomeID = 2
        tradeGroupID = 10
        # get initial cash
        makerInitialCash = contracts.cash.balanceOf(MAKER)
        takerInitialCash = contracts.cash.balanceOf(TAKER)
        marketInitialCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
        # Start makeOrder
        orderID = contracts.makeOrder.publicMakeOrder(orderType, fxpAmount, fxpPrice, marketID, outcomeID, 0, 0, tradeGroupID, sender=MAKER_KEY)
        # assert order and market cash
        order = contracts.orders.getOrder(orderID, orderType, marketID, outcomeID)
        assert(contracts.cash.balanceOf(contracts.info.getWallet(marketID)) - marketInitialCash == order[8]), "Increase in market's cash balance should equal money escrowed"
        assert(contracts.cash.balanceOf(contracts.info.getWallet(marketID)) == marketInitialCash + fxpExpectedCash), "Market's cash balance should be market Initial balance + (max - price)*amount"
        contracts._ContractLoader__state.mine(1)
        # Start takeOrder
        fxpAmountRemaining = contracts.takeOrder.publicTakeOrder(orderID, orderType, marketID, outcomeID, fxpAmount, sender=TAKER_KEY)
        # Final Assertions
        assert(fxpAmountRemaining == 0), "Amount remaining should be 0"
        assertions_ask_makerEscrowedCash_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID)
    def test_makerEscrowedShares_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY):
        # maker has shares in outcome, taker has shares of other outcomes
        t = contracts._ContractLoader__tester
        contracts._ContractLoader__state.mine(1)
        orderType = 2 # ask
        outcomeID = 1
        tradeGroupID = 10
        numOutcomes = contracts.markets.getMarketNumOutcomes(marketID)
        # make sure maker only has outcomeID shares...
        for i in range(0, numOutcomes):
            curOutcome = i + 1
            if (contracts.markets.getParticipantSharesPurchased(marketID, MAKER, curOutcome) > 0 and curOutcome != outcomeID):
                send_shares(contracts, marketID, MAKER, MAKER_KEY, curOutcome, TAKER)
        contracts._ContractLoader__state.mine(1)
        # get initial cash/shares
        makerInitialCash = contracts.cash.balanceOf(MAKER)
        takerInitialCash = contracts.cash.balanceOf(TAKER)
        marketInitialCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
        makerInitialShares = contracts.markets.getParticipantSharesPurchased(marketID, MAKER, outcomeID)
        # Start makeOrder
        orderID = contracts.makeOrder.publicMakeOrder(orderType, fxpAmount, fxpPrice, marketID, outcomeID, 0, 0, tradeGroupID, sender=MAKER_KEY)
        # assert order and market cash
        order = contracts.orders.getOrder(orderID, orderType, marketID, outcomeID)
        assert(makerInitialShares == order[9]), "Shares Escrowed should be = to the shares the maker started with"
        assert(makerInitialShares - order[9] == contracts.markets.getParticipantSharesPurchased(marketID, MAKER, 2)), "maker shouldn't have shares in outcomeID anymore"
        contracts._ContractLoader__state.mine(1)
        # Start takeOrder
        fxpAmountRemaining = contracts.takeOrder.publicTakeOrder(orderID, orderType, marketID, outcomeID, fxpAmount, sender=TAKER_KEY)
        # Final Assertions
        assert(fxpAmountRemaining == 0), "Amount remaining should be 0"
        assertions_ask_makerEscrowedShares_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID)
    def test_makerEscrowedCash_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY):
        # maker escrows cash, taker has complete set (shares of outcome)
        t = contracts._ContractLoader__tester
        outcomeShareContractWrapper = utils.makeOutcomeShareContractWrapper(contracts)
        contracts._ContractLoader__state.mine(1)
        orderType = 2 # ask
        fxpExpectedTakerGain = calculateHighSide(contracts, eventID, fxpAmount, fxpPrice)
        outcomeID = 2
        tradeGroupID = 10
        # taker first buys a complete set
        # buy the amount the taker plans to take from the order
        contracts._ContractLoader__state.mine(1)
        utils.buyCompleteSets(contracts, marketID, fxpAmount, TAKER_KEY)
        contracts._ContractLoader__state.mine(1)
        # get initial cash/shares
        makerInitialCash = contracts.cash.balanceOf(MAKER)
        takerInitialCash = contracts.cash.balanceOf(TAKER)
        marketInitialCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
        takerInitialShares = contracts.markets.getParticipantSharesPurchased(marketID, TAKER, outcomeID)
        # Start makeOrder
        orderID = contracts.makeOrder.publicMakeOrder(orderType, fxpAmount, fxpPrice, marketID, outcomeID, 0, 0, tradeGroupID, sender=MAKER_KEY)
        # assert order and market cash
        order = contracts.orders.getOrder(orderID, orderType, marketID, outcomeID)
        assert(contracts.cash.balanceOf(contracts.info.getWallet(marketID)) - marketInitialCash == order[8]), "Increase in market's cash balance should equal money escrowed"
        contracts._ContractLoader__state.mine(1)
        # Start takeOrder
        fxpAmountRemaining = contracts.takeOrder.publicTakeOrder(orderID, orderType, marketID, outcomeID, fxpAmount, sender=TAKER_KEY)
        # Final Assertions
        assert(fxpAmountRemaining == 0), "Amount remaining should be 0"
        assertions_ask_makerEscrowedCash_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID)
    def test_makerEscrowedShares_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY):
        # maker has shares in other outcome, taker has no shares
        t = contracts._ContractLoader__tester
        outcomeShareContractWrapper = utils.makeOutcomeShareContractWrapper(contracts)
        contracts._ContractLoader__state.mine(1)
        orderType = 2 # Ask
        outcomeID = 1
        tradeGroupID = 10
        fxpExpectedMakerGain = calculateLowSide(contracts, eventID, fxpAmount, fxpPrice)
        numOutcomes = contracts.markets.getMarketNumOutcomes(marketID)
        # transfer shares from taker to account 0 if taker has any shares
        # this is done because there should be shares from previous tests
        send_shares(contracts, marketID, TAKER, TAKER_KEY)
        # send any shares that aren't outcomeID (1) shares from maker to account 0
        for i in range(0, numOutcomes):
            curOutcome = i + 1
            if (contracts.markets.getParticipantSharesPurchased(marketID, MAKER, curOutcome) > 0 and curOutcome != outcomeID):
                send_shares(contracts, marketID, MAKER, MAKER_KEY, curOutcome)
        contracts._ContractLoader__state.mine(1)
        # get initial cash/shares
        makerInitialCash = contracts.cash.balanceOf(MAKER)
        takerInitialCash = contracts.cash.balanceOf(TAKER)
        marketInitialCash = contracts.cash.balanceOf(contracts.info.getWallet(marketID))
        makerInitialShares = contracts.markets.getParticipantSharesPurchased(marketID, MAKER, outcomeID)
        # Start makeOrder
        orderID = contracts.makeOrder.publicMakeOrder(orderType, fxpAmount, fxpPrice, marketID, outcomeID, 0, 0, tradeGroupID, sender=MAKER_KEY)
        # assert order and market cash
        order = contracts.orders.getOrder(orderID, orderType, marketID, outcomeID)
        assert(makerInitialShares == order[9]), "Shares Escrowed should be = to the shares the maker started with"
        assert(makerInitialShares - order[9] == contracts.markets.getParticipantSharesPurchased(marketID, MAKER, 2)), "maker shouldn't have shares in outcomeID anymore"
        contracts._ContractLoader__state.mine(1)
        # Start takeOrder
        fxpAmountRemaining = contracts.takeOrder.publicTakeOrder(orderID, orderType, marketID, outcomeID, fxpAmount, sender=TAKER_KEY)
        # Final Assertions
        assert(fxpAmountRemaining == 0), "Amount remaining should be 0"
        assertions_ask_makerEscrowedShares_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, marketInitialCash, makerInitialCash, takerInitialCash, outcomeID)
        # finally, transfer all shares to account 0 to close out or bid tests
        send_shares(contracts, marketID, MAKER, MAKER_KEY)
        send_shares(contracts, marketID, TAKER, TAKER_KEY)
    test_makerEscrowedCash_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    test_makerEscrowedShares_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    test_makerEscrowedCash_takerWithShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    test_makerEscrowedShares_takerWithoutShares(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)

def test_binary(contracts, i, MAKER, TAKER, MAKER_KEY, TAKER_KEY, amount=random.randint(1, 11), price=random.random()):
    # Test case:
    # binary event market
    t = contracts._ContractLoader__tester
    eventID = utils.createBinaryEvent(contracts)
    marketID = utils.createMarket(contracts, eventID)
    randomCheck = check_randoms(contracts, eventID, marketID, amount, price)
    while(randomCheck == 0):
        price = random.random()
        amount = random.randint(1, 11)
        randomCheck = check_randoms(contracts, eventID, marketID, amount, price)
    fxpAmount = utils.fix(amount)
    fxpPrice = utils.fix(price + utils.unfix(contracts.events.getMinValue(eventID)))
    # run all possible approvals now so that we don't need to do it in each test case
    approvals(contracts, eventID, marketID, amount, price, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    print "Start Fuzzy WCL tests - Binary Market - bidOrders. loop count:", i + 1
    print ""
    test_bidOrders(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    print ""
    print "Finished Fuzzy WCL tests - Binary Market - bidOrders. loop count:", i + 1
    print ""
    print "Start Fuzzy WCL tests - Binary Market - askOrders. loop count:", i + 1
    print ""
    test_askOrders(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    print ""
    print "Finished Fuzzy WCL tests - Binary Market - askOrders. loop count:", i + 1
    print ""

def test_categorical(contracts, i, MAKER, TAKER, MAKER_KEY, TAKER_KEY, amount=random.randint(1, 11), price=random.random(), numOutcomes=3):
    # Test case:
    # categorical event market
    t = contracts._ContractLoader__tester
    eventID = utils.createCategoricalEvent(contracts, numOutcomes)
    marketID = utils.createMarket(contracts, eventID)
    randomCheck = check_randoms(contracts, eventID, marketID, amount, price)
    while(randomCheck == 0):
        price = random.random()
        amount = random.randint(1, 11)
        randomCheck = check_randoms(contracts, eventID, marketID, amount, price)
    fxpAmount = utils.fix(amount)
    fxpPrice = utils.fix(price + utils.unfix(contracts.events.getMinValue(eventID)))
    # run all possible approvals now so that we don't need to do it in each test case
    approvals(contracts, eventID, marketID, amount, price, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    print "Start Fuzzy WCL tests - Categorical Market - bidOrders. loop count:", i + 1
    print ""
    test_bidOrders(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    print ""
    print "Finished Fuzzy WCL tests - Categorical Market - bidOrders. loop count:", i + 1
    print ""
    print "Start Fuzzy WCL tests - Categorical Market - askOrders. loop count:", i + 1
    print ""
    test_askOrders(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    print ""
    print "Finished Fuzzy WCL tests - Categorical Market - askOrders. loop count:", i + 1
    print ""

def test_scalar(contracts, i, MAKER, TAKER, MAKER_KEY, TAKER_KEY, amount=random.randint(1, 11), price=0, scalarMin=10, scalarMax=60):
    # Test case:
    # scalar event market
    t = contracts._ContractLoader__tester
    eventID = utils.createScalarEvent(contracts, utils.fix(scalarMin), utils.fix(scalarMax))
    marketID = utils.createMarket(contracts, eventID)
    if price == 0:
        price = random.randint(scalarMin, (scalarMax + 1))
    randomCheck = check_randoms(contracts, eventID, marketID, amount, price)
    while(randomCheck == 0):
        price = random.randint(scalarMin, (scalarMax + 1))
        amount = random.randint(1, 11)
        randomCheck = check_randoms(contracts, eventID, marketID, amount, price)
    fxpAmount = utils.fix(amount)
    fxpPrice = utils.fix(price)
    # run all possible approvals now so that we don't need to do it in each test case
    approvals(contracts, eventID, marketID, amount, price, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    print "Start Fuzzy WCL tests - Scalar Market - bidOrders. loop count:", i + 1
    print ""
    test_bidOrders(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    print ""
    print "Finished Fuzzy WCL tests - Scalar Market - bidOrders. loop count:", i + 1
    print ""
    print "Start Fuzzy WCL tests - Scalar Market - askOrders. loop count:", i + 1
    print ""
    test_askOrders(contracts, eventID, marketID, fxpAmount, fxpPrice, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    print ""
    print "Finished Fuzzy WCL tests - Scalar Market - askOrders. loop count:", i + 1
    print ""

# utility functions
def calculateLowSide(contracts, eventID, fxpAmount, fxpPrice):
    return int(Decimal(fxpAmount) * (Decimal(fxpPrice) - Decimal(contracts.events.getMinValue(eventID))) / Decimal(10)**Decimal(18))

def calculateHighSide(contracts, eventID, fxpAmount, fxpPrice):
    maxValue = contracts.events.getMaxValue(eventID)
    numOutcomes = contracts.events.getNumOutcomes(eventID)
    if numOutcomes > 2:
        # this is categorical, we should have fix(2) as the max value
        maxValue = utils.fix(2)
    return int(Decimal(fxpAmount) * (Decimal(maxValue) - Decimal(fxpPrice)) / Decimal(10)**Decimal(18))

# approves all contracts involved to spend money
def approvals(contracts, eventID, marketID, amount, price, MAKER, TAKER, MAKER_KEY, TAKER_KEY):
    t = contracts._ContractLoader__tester
    fxpAllowance = utils.fix(100*(price*amount))
    fxpEtherDepositValue = utils.fix(10*(price*amount))
    # deposit ETH to cash contract
    assert(contracts.cash.publicDepositEther(value=fxpEtherDepositValue, sender=MAKER_KEY) == 1), "publicDepositEther to MAKER should succeed"
    assert(contracts.cash.publicDepositEther(value=fxpEtherDepositValue, sender=TAKER_KEY) == 1), "publicDepositEther to TAKER should succeed"
    # begin approval process for all possible contracts
    assert(contracts.cash.approve(contracts.makeOrder.address, fxpAllowance, sender=MAKER_KEY) == 1), "Approve makeOrder contract to spend cash from MAKER"
    assert(contracts.cash.approve(contracts.makeOrder.address, fxpAllowance, sender=TAKER_KEY) == 1), "Approve makeOrder contract to spend cash from TAKER"
    assert(contracts.cash.approve(contracts.takeOrder.address, fxpAllowance, sender=MAKER_KEY) == 1), "Approve takeOrder contract to spend cash from MAKER"
    assert(contracts.cash.approve(contracts.takeOrder.address, fxpAllowance, sender=TAKER_KEY) == 1), "Approve takeOrder contract to spend cash from TAKER"
    assert(contracts.cash.approve(contracts.takeBidOrder.address, fxpAllowance, sender=MAKER_KEY) == 1), "Approve takeBidOrder contract to spend cash from MAKER"
    assert(contracts.cash.approve(contracts.takeBidOrder.address, fxpAllowance, sender=TAKER_KEY) == 1), "Approve takeBidOrder contract to spend cash from TAKER"
    assert(contracts.cash.approve(contracts.takeAskOrder.address, fxpAllowance, sender=MAKER_KEY) == 1), "Approve takeAskOrder contract to spend cash from MAKER"
    assert(contracts.cash.approve(contracts.takeAskOrder.address, fxpAllowance, sender=TAKER_KEY) == 1), "Approve takeAskOrder contract to spend cash from TAKER"
    assert(contracts.cash.approve(contracts.completeSets.address, fxpAllowance, sender=MAKER_KEY) == 1), "Approve completeSets contract to spend cash from MAKER"
    assert(contracts.cash.approve(contracts.completeSets.address, fxpAllowance, sender=TAKER_KEY) == 1), "Approve completeSets contract to spend cash from TAKER"
    numOutcomes = contracts.markets.getMarketNumOutcomes(marketID)
    outcomeShareContractWrapper = utils.makeOutcomeShareContractWrapper(contracts)
    contracts._ContractLoader__state.mine(1)
    for i in range(0, numOutcomes):
        outcomeID = i + 1
        outcomeShareContract = contracts.markets.getOutcomeShareContract(marketID, outcomeID)
        abiEncodedData = shareTokenContractTranslator.encode("approve", [contracts.takeOrder.address, fxpAllowance])
        assert(int(contracts._ContractLoader__state.send(MAKER_KEY, outcomeShareContract, 0, abiEncodedData).encode("hex"), 16) == 1), "Approve takeOrder contract to spend shares from the user's account (MAKER)"
        assert(int(contracts._ContractLoader__state.send(TAKER_KEY, outcomeShareContract, 0, abiEncodedData).encode("hex"), 16) == 1), "Approve takeOrder contract to spend shares from the user's account (TAKER)"
        abiEncodedData = shareTokenContractTranslator.encode("approve", [contracts.takeBidOrder.address, fxpAllowance])
        assert(int(contracts._ContractLoader__state.send(MAKER_KEY, outcomeShareContract, 0, abiEncodedData).encode("hex"), 16) == 1), "Approve takeBidOrder contract to spend shares from the user's account (MAKER)"
        assert(int(contracts._ContractLoader__state.send(TAKER_KEY, outcomeShareContract, 0, abiEncodedData).encode("hex"), 16) == 1), "Approve takeBidOrder contract to spend shares from the user's account (TAKER)"
        abiEncodedData = shareTokenContractTranslator.encode("approve", [contracts.takeAskOrder.address, fxpAllowance])
        assert(int(contracts._ContractLoader__state.send(MAKER_KEY, outcomeShareContract, 0, abiEncodedData).encode("hex"), 16) == 1), "Approve takeAskOrder contract to spend shares from the user's account (MAKER)"
        assert(int(contracts._ContractLoader__state.send(TAKER_KEY, outcomeShareContract, 0, abiEncodedData).encode("hex"), 16) == 1), "Approve takeAskOrder contract to spend shares from the user's account (TAKER)"
        abiEncodedData = shareTokenContractTranslator.encode("approve", [contracts.makeOrder.address, fxpAllowance])
        assert(int(contracts._ContractLoader__state.send(MAKER_KEY, outcomeShareContract, 0, abiEncodedData).encode("hex"), 16) == 1), "Approve makeOrder contract to spend shares from the user's account (MAKER)"
        assert(int(contracts._ContractLoader__state.send(TAKER_KEY, outcomeShareContract, 0, abiEncodedData).encode("hex"), 16) == 1), "Approve makeOrder contract to spend shares from the user's account (TAKER)"
        assert(outcomeShareContractWrapper.allowance(outcomeShareContract, TAKER, contracts.takeOrder.address) == fxpAllowance), "takeOrder contract's allowance should be equal to the amount approved"
        assert(outcomeShareContractWrapper.allowance(outcomeShareContract, MAKER, contracts.takeBidOrder.address) == fxpAllowance), "takeBidOrder contract's allowance should be equal to the amount approved"
        assert(outcomeShareContractWrapper.allowance(outcomeShareContract, MAKER, contracts.takeAskOrder.address) == fxpAllowance), "takeAskOrder contract's allowance should be equal to the amount approved"
        assert(outcomeShareContractWrapper.allowance(outcomeShareContract, TAKER, contracts.makeOrder.address) == fxpAllowance), "makeOrder contract's allowance should be equal to the amount approved"

# sends shares to account 0 if no toAddress is provided, otherwise can send shares to an address, used to move shares occasionally before tests
def send_shares(contracts, marketID, address, key, outcome=0, toAddress=0):
    # address is the account we plan to take shares away from (e.g. t.a2)
    t = contracts._ContractLoader__tester
    if toAddress == 0:
        toAddress = t.a0
    if outcome == 0:
        for i in range(0, contracts.markets.getMarketNumOutcomes(marketID)):
            outcome = i + 1
            shares = contracts.markets.getParticipantSharesPurchased(marketID, address, outcome)
            if shares != 0:
                outcomeShareContract = contracts.markets.getOutcomeShareContract(marketID, outcome)
                transferAbiEncodedData = shareTokenContractTranslator.encode("transfer", [toAddress, shares])
                assert(int(contracts._ContractLoader__state.send(key, outcomeShareContract, 0, transferAbiEncodedData).encode("hex"), 16) == 1), "Transfer shares of outcome to address 0"
    else:
        shares = contracts.markets.getParticipantSharesPurchased(marketID, address, outcome)
        if shares != 0:
            outcomeShareContract = contracts.markets.getOutcomeShareContract(marketID, outcome)
            transferAbiEncodedData = shareTokenContractTranslator.encode("transfer", [toAddress, shares])
            assert(int(contracts._ContractLoader__state.send(key, outcomeShareContract, 0, transferAbiEncodedData).encode("hex"), 16) == 1), "Transfer shares of outcome to address 0"

# assertions around shares
def check_shares(contracts, marketID, owner, expectedArray):
    t = contracts._ContractLoader__tester
    numOutcomes = contracts.markets.getMarketNumOutcomes(marketID)
    for i in range(0, numOutcomes):
        outcome = i + 1
        assert(contracts.markets.getParticipantSharesPurchased(marketID, owner, outcome) == expectedArray[i]), "Shares haven't been assigned as expected"

# check randomly generated numbers to make sure they aren't out of range
def check_randoms(contracts, eventID, marketID, amount, price):
    t = contracts._ContractLoader__tester
    fxpCumulativeScale = contracts.markets.getCumulativeScale(marketID) # 1
    fxpTradingFee = contracts.markets.getTradingFee(marketID) # 0.020...01
    if price > 1:
        # scalar
        fxpPricePerShare = utils.fix(price - utils.unfix(contracts.events.getMinValue(eventID)))
        # if we don't have a positive amount of pricePerShare this will fail, lets re-randomize
        if fxpPricePerShare <= 0:
            return 0
    else:
        # binary / categorical
        fxpPricePerShare = utils.fix(price)
        # if we don't have at least the tradingFee this will fail, lets re-randomize
        if fxpPricePerShare <= fxpTradingFee:
            return 0
    if (int((Decimal(fxpTradingFee) * Decimal(fxpCumulativeScale) / 10**18) + fxpPricePerShare) > fxpCumulativeScale):
        # if fees + cost of the shares are > range then the trade is a guaranteed losing proposition and we should use different random numbers
        return 0
    else:
        # these random numbers should work
        return 1

def test_wcl(contracts, amountOfTests=1):
    t = contracts._ContractLoader__tester
    print "Initiating Fuzzy WCL Tests"
    print "Amount of times looping through tests:", amountOfTests
    print ""
    # just picked some address that hopefully havent been used in other tests just incase we need a lot of money ;)
    MAKER = t.a5
    TAKER = t.a6
    MAKER_KEY = t.k5
    TAKER_KEY = t.k6
    def test_fuzzy_wcl():
        for i in range(0, amountOfTests):
            contracts._ContractLoader__state.mine(1)
            test_binary(contracts, i, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
            contracts._ContractLoader__state.mine(1)
            test_categorical(contracts, i, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
            contracts._ContractLoader__state.mine(1)
            test_scalar(contracts, i, MAKER, TAKER, MAKER_KEY, TAKER_KEY)
    test_fuzzy_wcl()
    print ""
    print "Fuzzy WCL Tests Complete"
    print "Amount of times looped through tests:", amountOfTests

if __name__ == '__main__':
    ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
    sys.path.insert(0, os.path.join(ROOT, "upload_contracts"))
    from upload_contracts import ContractLoader
    contracts = ContractLoader(os.path.join(ROOT, "src"), "controller.se", ["mutex.se", "cash.se", "repContract.se"])
    test_wcl(contracts, 20)
