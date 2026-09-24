# Quorum Coding Challenge - Legislative Data

This project implements a solution for the Quorum Coding Challenge to process and analyze legislative voting data.

## Project Overview

The objective is to process legislative datasets representing legislators, bills, votes, and vote results to generate two primary reports:

1. **Legislator Vote Summary (`legislators-support-oppose-count.csv`)**:
   - For every legislator, how many bills they supported (voted Yea) and opposed (voted Nay).
   - Columns: `id`, `name`, `num_supported_bills`, `num_opposed_bills`.

2. **Bill Vote & Sponsor Summary (`bills.csv`)**:
   - For every bill, how many legislators supported it, how many opposed it, and the name of the primary sponsor (or "Unknown" if missing).
   - Columns: `id`, `title`, `supporter_count`, `opposer_count`, `primary_sponsor`.

## Input Datasets

Located in `docs/challenge/`:
- `legislators.csv`: Legislator ID and name.
- `bills.csv`: Bill ID, title, and primary sponsor ID.
- `votes.csv`: Vote ID and associated bill ID.
- `vote_results.csv`: VoteResult ID, legislator ID, vote ID, and vote type (`1` = Yea, `2` = Nay).

## Challenge Documentation

Refer to [docs/challenge/Quorum Coding Challenge Legislative Data.pdf](docs/challenge/Quorum%20Coding%20Challenge%20Legislative%20Data.pdf) for the full challenge description and requirements.
