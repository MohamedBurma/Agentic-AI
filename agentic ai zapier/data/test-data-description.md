# Test Data Description

## Purpose

This phase introduces a small synthetic dataset for testing the operations agent. The dataset does not contain real people, private information, or production records.

## Test Categories

The test requests include:

- Valid meeting requests.
- Valid follow-up task requests.
- Valid operations record updates.
- Requests with missing information.
- Unsupported or high-impact requests.
- A possible duplicate request.
- An ambiguous request.

## Expected Results

The `expected-results.csv` file describes the expected classification, state, action, and policy decision for each request. These values are reference results for later evaluation; they are not presented as final system measurements.

## Mock System Tables

The files in the `mock-systems` directory represent simplified application tables:

- `mock-calendar.csv`: simulated calendar events.
- `mock-tasks.csv`: simulated follow-up tasks.
- `operations-tracker.csv`: simulated operations records.

The tables initially contain only their column definitions. Approved actions can add rows during the implementation and testing phases.

## Safety Note

The dataset is intended only for academic testing. The project will not use real calendars, real task systems, real customer records, or real financial actions.
