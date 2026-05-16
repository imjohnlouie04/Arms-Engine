---
name: pse-trading
agents:
  - arms-backend-agent
description: >
  Deep knowledge of how the Philippine Stock Exchange (PSE) works: trading sessions,
  order types, market mechanics, the ITCH/OUCH protocol feed, instrument reference data,
  and real session statistics derived from actual ITCH Total View data (replay date 2026-05-14).
  Use this skill whenever the user asks about PSE trading mechanics, session schedules,
  order book behavior, market data feeds, Philippine equities, lot sizes, circuit breakers,
  tick sizes, broker anonymity, auction uncrossing, or wants to analyse or build anything
  on top of PSE market data. Also trigger for questions about reading or parsing the ITCH
  binary/JSON feed, understanding message types (Add Order, Trade, Executed, BBO, etc.),
  or building trading systems for the Philippine market.
---

# PSE Trading Skill

This skill covers the complete mechanics of trading on the Philippine Stock Exchange,
grounded in both the official PSE Equities Feed Specification v2.2 (OMX / NASDAQ OMX
X-stream) and empirical analysis of a real ITCH Total View session (2026-05-14,
143 744 events, 393 instruments, 385 trading symbols).

Read `references/itch-messages.md` when the user needs detailed ITCH message field
layouts or parsing guidance. Read `references/session-data.md` for quantitative stats
from the real session.

---

## 1. Market Structure

### Boards
| Board code | Description |
|------------|-------------|
| `N`        | Normal board (continuous + auction) — 385 instruments |
| `O`        | Odd-lot board |
| `I`        | Index instruments — 8 in the session data |

All trading currencies are **PHP (Philippine Peso)**. Prices use **4 decimal places**
for equities; some instruments use 2.

### Instrument Reference Data (Orderbook Directory `[R]`)
Each instrument has:
- **book_id** – unique integer orderbook identifier used in all messages
- **symbol** – e.g. `BDO`, `JFC`, `ICT`
- **ISIN** – 12-character code (e.g. `PHY030431175`)
- **lot_size** – minimum board lot (1, 5, 10, 100, 1 000, 10 000, 100 000, 1 000 000)
- **price_decimals** – divisor for integer prices: `price = integer / 10^price_decimals`
- **instrument_type** – C=Common, P=Preferred, W=Warrant, E=ETF, D=PDR, I=Index

Common lot sizes in this session: 1 000 (118 instruments), 100 (92), 10 (85),
10 000 (49), 5 (27).

---

## 2. Daily Trading Schedule (PHT = UTC+8)

The sequence below is exact from the 2026-05-14 session:

| Time (PHT) | State Code | Description |
|------------|------------|-------------|
| 00:00:00   | `O`        | Start of Messages (midnight, feed goes live) |
| 09:00:00   | `S`        | **Pre-Open** – orders may be entered and amended |
| 09:15:00   | `R`        | **Pre-Open No Cancellation** – no cancels allowed |
| 09:30:00   | `Q`        | **Market Open** – auction uncross, continuous trading begins |
| 12:00:00   | `A`        | **Break Start** – midday trading break |
| 12:00:00   | `B`        | **Break End** – trading resumes (near-instant in this session) |
| 14:45:00   | `L`        | **Pre-Close** – closing auction phase |
| 14:48:00   | `J`        | **Pre-Close No Cancellation** |
| 14:50:00   | `P`        | **Trading At Last** – closing price set, limit orders only |
| 15:00:00   | `M`        | **End of Market Hours** |

System Event codes map 1-to-1 to ITCH `[S]` message Event Code field. These codes also
appear in the JSON feed's `market_state` field on `kind: "state"` events.

---

## 3. Trading Sessions in Detail

### Pre-Open (09:00–09:15)
- Orders can be entered, amended, cancelled
- Indicative auction price `[I]` messages published as the book builds
- No trades execute yet
- Auction type = `'O'` (Opening)

### Pre-Open No Cancellation (09:15–09:30)
- Orders may still be entered but **not cancelled**
- Allows fair price formation

### Continuous Trading (09:30–12:00 and ~12:00–14:45)
- Standard price-time priority order matching
- Incoming aggressive orders match against passive resting orders
- On a match: `Order Executed [E/e]` sent for the passive side; `Add Order [A]`
  sent for any unmatched remainder of the aggressor
- Suspensions use `[H]` with state `V`+reason `S`; freeze uses `V`+`F`
- Intraday halts: `[H]` state `T`+reason `H`, triggers intraday auction (`[I]` type `I`)

### Midday Break (12:00)
In this session the break was near-instant (A and B events at the same second).

### Pre-Close / Closing Auction (14:45–14:50)
- Closing auction collects orders, uncrosses at close price
- `[C/c]` (Order Executed With Price) messages for auction fills
- Auction type = `'C'` (Closing)

### Trading At Last (14:50–15:00)
- Close price already determined
- Limit orders can execute only at the exact close price
- `[P/p]` Trade messages used here
- A special `[P]` with `match_number=0` and `executed_quantity=0` signals the **close price**

---

## 4. Order Book Mechanics

### Adding Orders
`Add Order [A]` message fields: order_number, side (B/S), quantity, orderbook, price.
- A market order uses sentinel price `0x7FFFFFFF` (2 147 483 647)
- An `[A]` with order_number=0 AND quantity=0 is a **reference price update**, not a real order

### Order Lifecycle
```
Add Order [A]  →  resting in book
   ↓ partial fill
Order Executed [E/e]    (passive side; price from the book)
Order Executed With Price [C/c]  (auction fills or thaw-after-freeze)
   ↓ remaining balance
Add Order [A]  (aggressor remainder) or nothing if fully matched
   ↓ cancel
Order Delete [D]
   ↓ amend
Order Replace [U]  (new order_number assigned)
```

### Broker Anonymity
PSE can run with or without broker identity disclosure:

| Mode | Messages used |
|------|---------------|
| Broker Anonymity ON  | `[E]`, `[C]`, `[P]` (no broker IDs) |
| Broker Anonymity OFF | `[e]`, `[c]`, `[p]` (include passive/active broker IDs) |

### Broken Trades
`[B]` Broken Trade references a prior match_number. Only reason currently: `S` (Supervisory).

---

## 5. Price & Quantity Rules

### Price Calculation
```
actual_price = integer_price / 10^price_decimals
```
For price_decimals=4: integer 7852614 → PHP 785.2614

### Circuit Breakers (from `[k]` Orderbook Restrictions)
- **Static collars**: High Collar / Low Collar – absolute price limits
- **Dynamic CB**: CB Limit Up % and CB Limit Down % from last traded price
- Freeze triggered → `[H]` state `V`+reason `F` → intraday auction → thaw → `[C/c]` fills

### Foreign Ownership
`[f]` Foreign Shares Available message: sent per Product Code for instruments that allow
foreign ownership. Sign field indicates `+` or `–` balance. Not sent for instruments
with no foreign ownership limit.

---

## 6. ITCH Feed Types

| Feed | Key messages | Use case |
|------|-------------|----------|
| **Total View** | All messages including full order book depth | Full reconstruction |
| **Basic with Last Sale** | BBO `[O]`, Trades `[P/p]`, no individual orders | Lightweight quote feed |
| **News** | `[N]` News Items only | Disclosure / iNav feed |
| **Index** | `[Z]` Index Value, `[Y]` Index Member Directory | Index tracking |

### BBO Quotation `[O]` (Basic feed)
- Best bid price/size and best offer price/size
- Sentinel `Best_Bid_Size = 0x7FFFFFFFFFFFFFFF` → reference price update (not real quote)

### Index Value `[Z]`
Sent dynamically throughout the day. `Index Orderbook` field cross-references `[R]`.

---

## 7. News Feeds

### iNav (ETF intraday NAV)
Sent every 1 minute via `[N]` message:
- FirmId = `EXCH`
- Title format: `symbol:FMETF,timestamp:09/11/2014 14:19:00`
- NewsText: `iNAV:116.7204,PDiNAV:116.8579`

### Company Disclosures & Exchange Notices (PSE EDGE)
Also via `[N]`:
- Orderbook = 0 for Listing Notices / Disclosure Notices
- Reference field = URL on edge.pse.com.ph
- Templates: Company Announcement, Financial Report, Other Report, Listing Notice, Disclosure Notice

---

## 8. Working with PSE ITCH Data

### Native Format: Binary `.dat` files
The live PSE feed is delivered as a **binary ITCH stream** over:
- **SoupBinTCP v3.0** — point-to-point, requires login (username/password, case-sensitive)
- **MoldUDP64** — one-to-many UDP multicast, sequenced and recoverable

The raw `.dat` file is the binary payload — a sequence of fixed-width ITCH messages
prefixed by their 2-byte length. Each message starts with a 1-byte Type field that
identifies the message kind (see `references/itch-messages.md` for all field layouts).

**Parsing a raw ITCH .dat stream in Python:**
```python
import struct

def parse_itch_stream(filepath):
    with open(filepath, "rb") as f:
        while True:
            header = f.read(2)
            if len(header) < 2:
                break
            msg_len = struct.unpack(">H", header)[0]
            msg = f.read(msg_len)
            if len(msg) < msg_len:
                break
            msg_type = chr(msg[0])
            yield msg_type, msg

for msg_type, raw in parse_itch_stream("MarketITCHTV.dat"):
    if msg_type == "T":
        seconds = struct.unpack_from(">I", raw, 1)[0]
    elif msg_type == "A":
        order_no, = struct.unpack_from(">Q", raw, 5)
        # order_no == 0 means reference price update, not a real order
```

### JSON Conversion (for analysis / reference)
The `.dat` file can be decoded to JSON for easier inspection. The schema used in
`MarketITCHTV.json` collapses the full ITCH message set into two simplified event kinds:

**`kind: "state"`** — market phase transitions (from `[S]` System Event messages)
```json
{"kind":"state","timestamp":1778722200,"sequence":4119,"symbol":null,
 "price":null,"quantity":0,"market_state":"Q"}
```
`market_state` uses the same codes as ITCH `[S]` Event Code.

**`kind: "tick"`** — individual trade prints (from `[E]`, `[C]`, `[P]` and broker-ID variants)
```json
{"kind":"tick","timestamp":1778720420,"sequence":2,"symbol":"ICT",
 "price":785.2614,"quantity":215470,"market_state":null}
```
`timestamp` is Unix epoch seconds (UTC). Add 28 800 (8 hours) to get PHT.
`price` is already divided by `10^price_decimals` — it's the human-readable float.

**Reading the JSON for analysis:**
```python
import json, datetime

with open("MarketITCHTV.json") as f:
    data = json.load(f)

sym_info = {d["symbol"]: d for d in data["directories"]}
states = [e for e in data["events"] if e["kind"] == "state"]
ticks  = [e for e in data["events"] if e["kind"] == "tick"]

def to_pht(unix_ts):
    return datetime.datetime.utcfromtimestamp(unix_ts + 8*3600)
```

When building production systems, always parse from the binary `.dat` / live stream.
Use JSON only for debugging, backtesting, or offline analysis.

---

## 9. Key Statistics from 2026-05-14 Session

See `references/session-data.md` for the full tables. Highlights:

- **143 725 trade ticks** across **385 symbols**
- **Trading window**: 09:00:20 → 14:59:58 PHT
- Highest tick volume hour: **10:00–11:00** (44 834 ticks)
- Top stocks by **value traded**:

| Symbol | Value (PHP) | Trades | Shares |
|--------|-------------|--------|--------|
| ICT    | 1.88 B      | 6 845  | 2.38 M |
| BDO    | 1.09 B      | 12 342 | 9.06 M |
| BPI    | 819 M       | 10 718 | 8.92 M |
| JFC    | 452 M       | 9 463  | 3.24 M |
| SM     | 427 M       | 3 055  | 691 K  |

- Price range across all instruments: PHP 0.0046 (penny stocks) → PHP 4 430.00

---

## 10. Common Questions & Answers

**Q: Why does my price look like a huge integer?**
Divide by `10^price_decimals` from the `[R]` directory message for that orderbook.
For most equities, price_decimals=4, so divide by 10 000.

**Q: How do I reconstruct VWAP?**
Sum `price × quantity` across all ticks for the symbol, divide by total quantity.
Only count `Printable='Y'` executions.

**Q: What is a reference price?**
Sent as `[A]` with order_number=0, quantity=0 (Total View) or `[O]` with
`Best_Bid_Size=0x7FFFFFFFFFFFFFFF` (Basic). It's the price used as the base for
dynamic circuit breakers.

**Q: How do I know if broker IDs are included?**
Look for message type `[e]`/`[c]`/`[p]` vs `[E]`/`[C]`/`[P]`. Only one set is
active per session depending on broker anonymity policy.

**Q: How do I get the closing price?**
A `[P]`/`[p]` Trade message where both `match_number` and `executed_quantity` are 0
carries the close price in the `execution_price` field. Sent after the `P` (Trading At
Last) System Event.
