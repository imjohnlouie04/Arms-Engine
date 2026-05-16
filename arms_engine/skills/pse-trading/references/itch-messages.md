# ITCH Message Field Reference

Derived from PSE Equities Feed Specification v2.2 (19 March 2015, OMX Technology AB).
All integers are unsigned big-endian binary. All prices are integers divided by `10^price_decimals`.

## Table of Contents
1. [Time & System Messages](#time--system)
2. [Reference Data Messages](#reference-data)
3. [Order Book Messages](#order-book)
4. [Trade & Execution Messages](#trade--execution)
5. [Quote & Index Messages](#quote--index)
6. [News Messages](#news)

---

## Time & System

### [T] Time Stamp – Seconds
| Field   | Offset | Len | Type    | Notes |
|---------|--------|-----|---------|-------|
| Type    | 0      | 1   | Alpha   | "T" |
| Second  | 1      | 4   | Integer | Seconds since midnight |

### [S] System Event
| Field      | Offset | Len | Type    | Notes |
|------------|--------|-----|---------|-------|
| Type       | 0      | 1   | Alpha   | "S" |
| Timestamp  | 1      | 4   | Integer | Nanoseconds since last [T] |
| Group      | 5      | 8   | Alpha   | "N"=Normal, "O"=Oddlot, "I"=Index; blank=system level |
| Event Code | 13     | 1   | Alpha   | See session schedule codes |
| Orderbook  | 14     | 4   | Integer | 0 if system/group level |

**Event Codes:** O=Start, S=PreOpen, R=PreOpen-NoCancellation, Q=Open,
A=BreakStart, B=BreakEnd, L=PreClose, J=PreClose-NoCancellation, P=TradingAtLast,
M=EndOfMarket, E=EndOfSystem, C=EndOfMessages

### [s] Trading Schedule
Same as [S] plus:
| Field          | Offset | Len | Type    | Notes |
|----------------|--------|-----|---------|-------|
| Scheduled Time | 18     | 4   | Integer | Seconds past midnight |

---

## Reference Data

### [R] Orderbook Directory
| Field                  | Offset | Len | Type    |
|------------------------|--------|-----|---------|
| Type                   | 0      | 1   | Alpha   |
| Timestamp              | 1      | 4   | Integer |
| Orderbook              | 5      | 4   | Integer |
| Price Type             | 9      | 1   | Alpha   | U=per unit, P=percentage |
| ISIN                   | 10     | 12  | Alpha   |
| Sec Code               | 22     | 12  | Alpha   |
| Currency               | 34     | 3   | Alpha   |
| Group                  | 37     | 8   | Alpha   |
| Lot Size               | 45     | 8   | Integer |
| Qty Tick Size Table Id | 53     | 4   | Integer |
| Price Tick Size Table  | 57     | 4   | Integer |
| Price Decimals         | 61     | 4   | Integer |
| Delisting Date         | 65     | 4   | Integer | YYYYMMDD; 0=none |
| Delisting Time         | 69     | 4   | Integer | HHMMSS |
| Instrument Type        | 73     | 1   | Alpha   | C/P/W/E/D/I |
| Shares                 | 74     | 8   | Integer | Shares outstanding |
| Product Code           | 82     | 8   | Alpha   |

### [k] Orderbook Restrictions
| Field           | Offset | Len | Type    | Notes |
|-----------------|--------|-----|---------|-------|
| Orderbook       | 5      | 4   | Integer |
| Short Sell      | 9      | 1   | Alpha   | Y/N/B(uyback only) |
| High Collar     | 10     | 4   | Integer | 0x7FFFFFFF = no limit |
| Low Collar      | 14     | 4   | Integer | 0x7FFFFFFF = no limit |
| CB Limit Up %   | 18     | 4   | Integer | 0 = no limit |
| CB Limit Down % | 22     | 4   | Integer | 0 = no limit |
| CB Limit Dec    | 26     | 4   | Integer | Decimals for CB% values |

### [L] Price Tick Size
| Field             | Offset | Len |
|-------------------|--------|-----|
| Tick Size Table Id| 5      | 4   |
| Tick Size         | 9      | 4   |
| Price Start       | 13     | 4   |

### [M] Quantity Tick Size
| Field             | Offset | Len | Notes |
|-------------------|--------|-----|-------|
| Tick Size Table Id| 5      | 4   |
| Tick Size         | 9      | 8   | 0=Qty Start is max allowed |
| Quantity Start    | 17     | 8   |

### [Y] Index Member Directory
| Field           | Offset | Len |
|-----------------|--------|-----|
| Index Orderbook | 5      | 4   |
| Member Orderbook| 9      | 4   |
| Index Weight    | 13     | 8   | % using index price_decimals |

### [f] Foreign Shares Available
| Field                  | Offset | Len | Notes |
|------------------------|--------|-----|-------|
| Product Code           | 5      | 8   | Alpha |
| Ownership Rule ID      | 13     | 2   | Alpha |
| Sign                   | 15     | 1   | + or – |
| Foreign Shares Avail   | 16     | 8   | Integer |

---

## Order Book

### [H] Orderbook Trading Action
| Field         | Offset | Len | Notes |
|---------------|--------|-----|-------|
| Orderbook     | 5      | 4   |
| Trading State | 9      | 1   | T=Trading, V=Suspended |
| Reason        | 10     | 1   | N=Normal, S=Suspended, F=Frozen(CB), H=Halted |

Sent for all orderbooks at SOD to establish initial state.

### [A] Add Order
| Field        | Offset | Len | Notes |
|--------------|--------|-----|-------|
| Order Number | 5      | 8   | 0 = reference price update |
| Order Verb   | 13     | 1   | B=Buy, S=Sell; blank if ref price |
| Quantity     | 14     | 8   | 0 = reference price update |
| Orderbook    | 22     | 4   |
| Price        | 26     | 4   | 0x7FFFFFFF = market or ref unavailable |

### [D] Order Delete
| Field        | Offset | Len |
|--------------|--------|-----|
| Order Number | 5      | 8   |

### [U] Order Replace
| Field              | Offset | Len | Notes |
|--------------------|--------|-----|-------|
| Original Order No  | 5      | 8   |
| New Order Number   | 13     | 8   |
| Quantity           | 21     | 8   | New open quantity |
| Price              | 29     | 4   | 0x7FFFFFFF = market |

### [I] Indicative Price/Quantity
| Field                  | Offset | Len | Notes |
|------------------------|--------|-----|-------|
| Theoretical Auction Qty| 5      | 8   |
| Orderbook              | 13     | 4   |
| Best Bid               | 17     | 4   |
| Best Offer             | 21     | 4   |
| Theoretical Auction Px | 25     | 4   |
| Auction Type           | 29     | 1   | O=Opening, I=Intraday, C=Closing |

---

## Trade & Execution

### [E] Order Executed (broker anonymity ON)
| Field            | Offset | Len |
|------------------|--------|-----|
| Order Number     | 5      | 8   |
| Executed Qty     | 13     | 8   |
| Match Number     | 21     | 8   |

### [e] Order Executed with Broker ID (anonymity OFF)
Adds:
| Field            | Offset | Len |
|------------------|--------|-----|
| Passive Broker ID| 29     | 4   |
| Active Broker ID | 33     | 4   |

### [C] Order Executed With Price (broker anonymity ON)
| Field            | Offset | Len | Notes |
|------------------|--------|-----|-------|
| Order Number     | 5      | 8   |
| Executed Qty     | 13     | 8   |
| Match Number     | 21     | 8   |
| Printable        | 29     | 1   | Y=include in stats, N=exclude |
| Execution Price  | 30     | 4   |

### [c] Order Executed With Price and Broker ID (anonymity OFF)
Adds broker IDs at offsets 34 (passive) and 38 (active).

### [P] Trade (broker anonymity ON)
| Field           | Offset | Len | Notes |
|-----------------|--------|-----|-------|
| Executed Qty    | 5      | 8   | 0 = close price message |
| Orderbook       | 13     | 4   |
| Printable       | 17     | 1   |
| Execution Price | 18     | 4   |
| Match Number    | 22     | 8   | 0 = close price message |
| Trade Indicator | 30     | 1   | ' '=regular, C=cross, B=block, M=manual |

Close price: both Executed Qty=0 AND Match Number=0.

### [p] Trade with Broker ID (anonymity OFF)
Adds:
| Field        | Offset | Len |
|--------------|--------|-----|
| Buy Broker   | 31     | 4   |
| Sell Broker  | 35     | 4   |

### [B] Broken Trade
| Field        | Offset | Len | Notes |
|--------------|--------|-----|-------|
| Match Number | 5      | 8   | Refers to prior E/C/P match |
| Reason       | 13     | 1   | S=Supervisory |

---

## Quote & Index

### [O] BBO Quotation
| Field          | Offset | Len | Notes |
|----------------|--------|-----|-------|
| Orderbook      | 5      | 4   |
| Best Bid Price | 9      | 4   | 0x7FFFFFFF = no depth / ref unavailable |
| Best Bid Size  | 13     | 8   | 0x7FFFFFFFFFFFFFFF = reference price update |
| Best Offer Price| 21    | 4   |
| Best Offer Size | 25    | 8   |

### [Z] Index Value
| Field           | Offset | Len |
|-----------------|--------|-----|
| Index Orderbook | 5      | 4   |
| Value           | 9      | 8   |

---

## News

### [N] News Item
| Field     | Offset  | Len           | Type              |
|-----------|---------|---------------|-------------------|
| Orderbook | 5       | 4             | Integer; 0=exchange-wide |
| NewsId    | 9       | 4             | Integer; 0=not set |
| FirmId    | 13      | 30            | Alpha |
| Title     | 43      | max 81        | Null-terminated Alpha |
| Reference | varies  | max 256       | Null-terminated Alpha (URL) |
| NewsText  | varies  | max 512       | Null-terminated Alpha |
