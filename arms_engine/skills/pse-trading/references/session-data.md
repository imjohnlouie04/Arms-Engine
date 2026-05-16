# PSE Session Data — 2026-05-14

Source: MarketITCHTV.dat (real PSE ITCH Total View binary capture, decoded to JSON for analysis)
- Replay date: 2026-05-14
- Source SHA-256: f478d5d5cc0a91bca16f4e523300e9e75585bce5904aa6364566aad159964c34
- Native format: binary ITCH stream (SoupBinTCP/MoldUDP64); JSON is a derived convenience format
- Instruments (directories): 393 (385 Normal board + 8 Index)
- Total events: 143 744 (143 725 ticks + 19 state transitions)
- Unique trading symbols: 385
- Trading window (PHT): 09:00:20 → 14:59:58

---

## Session Timeline

| Time (PHT) | State | Description |
|------------|-------|-------------|
| 00:00:00   | O     | Start of Messages |
| 09:00:00   | S     | Pre-Open begins |
| 09:15:00   | R     | Pre-Open No Cancellation |
| 09:30:00   | Q     | Market Open — continuous trading |
| 12:00:00   | A     | Break Start |
| 12:00:00   | B     | Break End (near-instant) |
| 14:45:00   | L     | Pre-Close |
| 14:48:00   | J     | Pre-Close No Cancellation |
| 14:50:00   | P     | Trading At Last |
| 15:00:00   | M     | End of Market Hours |

---

## Hourly Trade Activity

| Hour (PHT) | Ticks   | Shares          | Value (PHP)     |
|------------|---------|-----------------|-----------------|
| 09:00      | 22 913  | 137 394 308     | 2 120 826 500   |
| 10:00      | 44 834  | 155 678 374     | 2 000 646 391   |
| 11:00      | 37 969  | 167 817 241     | 1 365 184 469   |
| 12:00      | 63      | 123 535         | 2 133 828       |
| 13:00      | 15 477  | 142 512 620     | 1 082 572 306   |
| 14:00      | 22 469  | 169 483 843     | 2 623 372 645   |
| **Total**  | **143 725** | **773 009 921** | **~9.19 B** |

Peak hour is **10:00–11:00** (44 834 ticks). Lowest is the midday break (63 ticks).
The **14:00 hour** has the highest value traded despite fewer ticks — driven by
large-lot closing activity and high-priced stocks.

---

## Top 20 Stocks by Value Traded

| Rank | Symbol | Value (PHP)   | Trades | Shares      | Low      | High     | Last     |
|------|--------|---------------|--------|-------------|----------|----------|----------|
| 1    | ICT    | 1 882 877 309 | 6 845  | 2 380 370   | 785.2092 | 804.0000 | 792.0000 |
| 2    | BDO    | 1 091 981 800 | 12 342 | 9 064 579   | 119.2000 | 122.8000 | 120.0000 |
| 3    | BPI    | 819 939 038   | 10 718 | 8 916 520   | 88.0000  | 94.8000  | 94.8000  |
| 4    | JFC    | 452 219 690   | 9 463  | 3 240 936   | 135.0000 | 143.5000 | 140.0000 |
| 5    | SM     | 426 574 636   | 3 055  | 691 072     | 602.5000 | 628.0000 | 628.0000 |
| 6    | GLO    | 407 304 750   | 4 472  | 232 801     | 1700.000 | 1766.000 | 1765.000 |
| 7    | PGOLD  | 312 942 452   | 1 881  | 6 710 540   | 46.3000  | 48.0000  | 46.8500  |
| 8    | RRHI   | 212 646 720   | 954    | 4 429 151   | 47.8000  | 48.1000  | 48.1000  |
| 9    | MYNLD  | 205 056 851   | 4 093  | 8 449 884   | 24.1000  | 24.9500  | 24.3000  |
| 10   | PLUS   | 198 639 804   | 5 058  | 17 428 837  | 10.9000  | 12.0200  | 11.4000  |
| 11   | MER    | 168 000 856   | 3 040  | 265 380     | 630.0000 | 646.5000 | 630.0000 |
| 12   | APX    | 164 940 930   | 2 804  | 9 638 206   | 16.5600  | 17.6000  | 17.6000  |
| 13   | CNVRG  | 158 029 505   | 3 854  | 14 051 383  | 11.1400  | 11.7800  | 11.2000  |
| 14   | GTCAP  | 145 385 124   | 1 555  | 320 398     | 447.0000 | 463.0000 | 460.0000 |
| 15   | SGP    | 137 492 872   | 2 750  | 4 809 826   | 28.3000  | 33.2000  | 28.4000  |
| 16   | MBT    | 126 785 823   | 5 795  | 1 924 060   | 65.5000  | 68.9500  | 65.8500  |
| 17   | TEL    | 126 081 214   | 1 802  | 101 362     | 1225.000 | 1250.064 | 1236.000 |
| 18   | ALI    | 125 328 402   | 3 567  | 8 028 071   | 15.3600  | 16.0000  | 15.6000  |
| 19   | WEB    | 122 829 073   | 1 167  | 10 546 214  | 11.0800  | 12.0800  | 11.8800  |
| 20   | JGS    | 110 602 062   | 2 101  | 4 268 078   | 25.5000  | 27.6000  | 26.4000  |

---

## Top 20 Stocks by Trade Count

| Rank | Symbol | Trades | Shares      | Value (PHP)   |
|------|--------|--------|-------------|---------------|
| 1    | BDO    | 12 342 | 9 064 579   | 1 091 981 800 |
| 2    | BPI    | 10 718 | 8 916 520   | 819 939 038   |
| 3    | JFC    | 9 463  | 3 240 936   | 452 219 690   |
| 4    | ICT    | 6 845  | 2 380 370   | 1 882 877 309 |
| 5    | MBT    | 5 795  | 1 924 060   | 126 785 823   |
| 6    | PLUS   | 5 058  | 17 428 837  | 198 639 804   |
| 7    | GLO    | 4 472  | 232 801     | 407 304 750   |
| 8    | MYNLD  | 4 093  | 8 449 884   | 205 056 851   |
| 9    | CNVRG  | 3 854  | 14 051 383  | 158 029 505   |
| 10   | ALI    | 3 567  | 8 028 071   | 125 328 402   |
| 11   | AREIT  | 3 401  | 2 775 624   | 106 231 515   |
| 12   | URC    | 3 096  | 971 093     | 59 381 170    |
| 13   | SM     | 3 055  | 691 072     | 426 574 636   |
| 14   | MER    | 3 040  | 265 380     | 168 000 856   |
| 15   | APX    | 2 804  | 9 638 206   | 164 940 930   |
| 16   | DHI    | 2 783  | 8 000 694   | 70 967 620    |
| 17   | SGP    | 2 750  | 4 809 826   | 137 492 872   |
| 18   | DITO   | 2 156  | 80 054 342  | 64 173 123    |
| 19   | RCR    | 2 132  | 1 635 671   | 11 505 803    |
| 20   | JGS    | 2 101  | 4 268 078   | 110 602 062   |

---

## Instrument Profile Summary

| Category             | Count |
|----------------------|-------|
| Normal board (N)     | 385   |
| Index (I)            | 8     |
| Price decimals = 4   | 385   |
| Price decimals = 2   | 8     |

### Lot Size Distribution
| Lot Size  | Instruments |
|-----------|-------------|
| 1 000 000 | 7           |
| 100 000   | 7           |
| 10 000    | 49          |
| 1 000     | 118         |
| 100       | 92          |
| 10        | 85          |
| 5         | 27          |
| 1         | 8           |

### Price Range (all ticks)
- Minimum: PHP 0.0046
- Maximum: PHP 4 430.0000
- Most liquid mid-range: PHP 10–200 (banking, telco, conglomerates)
