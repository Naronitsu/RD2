# Minimal, Resource-Bounded Runtime Verification for a Safety-Critical Automotive ECU

## Name
Damian Navarro 6.3B

## Abstract
This project investigates a minimal runtime verification (RV) pipeline for safety-critical automotive ECU telemetry under resource constraints. A Spring-based replay service processes full ECU traces (68,433 rows per run), while LARVA-generated monitors evaluate four safety-related properties: time progression consistency, voltage range validity under load, coolant temperature bounds, and throttle/load-MAP behavioral checks. The study uses a controlled quantitative experiment with RV enabled versus disabled over clean and injected-abnormal datasets, reporting elapsed time, throughput, process CPU time, heap-delta indicators, and violation flag totals.

Results show that naive generated monitoring can introduce substantial overhead in abnormal paths, primarily due to expensive logging and bad-state stacktrace construction in hot paths rather than core predicate evaluation. After optimization (logging control and removal of bad-state stacktrace string construction), overhead is reduced to low double-digit percentages while preserving violation detection behavior. The findings support the feasibility of lightweight, monitor-based assurance for server-side automotive telemetry analysis, and highlight practical implementation details that strongly influence runtime cost in applied RV deployments.

## Video Explanation:
https://drive.google.com/file/d/-1BcJMKaucKGygJZNofPdzZOUfcgnjcb5n/view?usp=drive_link

## Live Prototype Demo:
https://drive.google.com/file/d/12woxcr2BVSZ9-HxxurWqdr8GjIporP7e/view?usp=sharing

